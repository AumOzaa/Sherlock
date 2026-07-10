# engine.py
import json
from ollama import chat
from pydantic import BaseModel
from typing import Literal
from models import ParticipantState

# Check schema for AI response
class RoleClassification(BaseModel):
    role: Literal["INTERVIEWER", "CANDIDATE", "NEUTRAL"]
    reason: str

class IdentityEngine:
    def __init__(self):
        self.metadata = {}
        self.participants = {}
        self.global_speaking_time = 0.0
        self.llm_model = "llama3.2:latest" 

        # TODO: Can add proper logging (for later)
    def initialize_metadata(self, metadata):
        self.metadata = metadata

    def process_event(self, event):
        p_id = event.get("participant_id")
        e_type = event.get("type")
        
        if p_id and p_id not in self.participants:
            self.participants[p_id] = ParticipantState(p_id, event.get("display_name", "Unknown"))

        if e_type == "webcam_change":
            self.participants[p_id].is_webcam_on = (event["status"] == "ON")
        elif e_type == "audio_activity":
            duration = event["duration_seconds"]
            self.participants[p_id].total_speaking_time += duration
            self.global_speaking_time += duration
        elif e_type == "transcript_chunk":
            self.participants[p_id].transcript_buffer.append(event["text"])
            self._evaluate_transcript_with_llm(p_id, event["text"])
        elif e_type == "leave":
            # If they leave, reset their confidence so the tracker targets the active session
            self.participants[p_id].confidence_score = 0.0
            self.participants[p_id].reasoning = "Participant disconnected from the meeting call."

        self._recalculate_all_scores()
    def _evaluate_transcript_with_llm(self, p_id, text):
        """Phase 3: Real-Time Local LLM classification using Ollama"""
        system_prompt = (
            f"You are a real-time behavioral classifier for an interview tracking system.\n"
            f"Expected Candidate Name: {self.metadata.get('candidate_name')}\n"
            f"Expected Interviewers: {', '.join(self.metadata.get('interviewers', []))}\n\n"
            f"Analyze the provided transcript slice and strictly identify if the speaker's behavioral pattern "
            f"matches an INTERVIEWER (welcoming, framing questions, evaluating), a "
            f"CANDIDATE (answering engineering concepts, introducing background), or NEUTRAL (chit-chat, brief greetings)."
        )

        try:
            # Checking the ollama api call
            print(f"[Ollama Call] Sending text from {p_id} to model '{self.llm_model}'...")
            
            response = chat(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Transcript Chunk from participant: '{text}'"}
                ],
                format=RoleClassification.model_json_schema(),
                options={"temperature": 0.0}
            )

            result = RoleClassification.model_validate_json(response.message.content)
            print(f"[Ollama Success] Model returned verdict: {result.role}")
            
            if result.role in ["CANDIDATE", "INTERVIEWER"]:
                self.participants[p_id].role_verdict = result.role
                
        except Exception as e:
            # CRITICAL DEBUG: Print the actual error causing it to fail
            print(f"[Ollama Error] Connection or validation failed: {e}")

    def _recalculate_all_scores(self):
        candidate_name = self.metadata.get("candidate_name", "")
        interviewers = self.metadata.get("interviewers", [])
        
        # Pass 1: Handle Base Naming Rules
        for p in self.participants.values():
            if p.role_verdict != "INTERVIEWER":
                p.calculate_base_name_score(candidate_name, interviewers)

        # Pass 2: Process of Elimination Rule
        non_interviewers = [p for p in self.participants.values() if p.role_verdict != "INTERVIEWER"]
        if len(non_interviewers) == 1 and non_interviewers[0].confidence_score < 60.0:
            target = non_interviewers[0]
            target.confidence_score = 75.0
            target.reasoning = "Process of elimination: All other participants are identified interviewers."

        # Pass 3: Behavioral Overrides
        for p in self.participants.values():
            if p.role_verdict == "INTERVIEWER":
                p.confidence_score = 0.0
                continue

            if p.role_verdict == "UNKNOWN" and p.confidence_score < 75.0:
                self._handle_candidate_rejoin_heuristics(p.id)
                
            if p.role_verdict == "CANDIDATE":
                p.confidence_score = max(p.confidence_score, 95.0)
                p.reasoning = "High confidence: Conversation transcript explicitly matches an interviewee profile."
            
            if self.global_speaking_time > 0:
                share = p.total_speaking_time / self.global_speaking_time
                if share > 0.40 and p.role_verdict != "INTERVIEWER":
                    p.confidence_score = min(p.confidence_score + 10, 99.0)
    def _handle_candidate_rejoin_heuristics(self, new_p_id):
            """
            Looks for disconnected candidate history to see if this new 
            unknown participant is actually the candidate rejoining.
            """
            new_p = self.participants[new_p_id]
            
            # Look for any historical participant who was highly likely to be the candidate but left
            for old_id, old_p in self.participants.items():
                if old_id == new_p_id:
                    continue
                    
                # If an old candidate recently left, and the new person has their webcam ON
                if old_p.role_verdict == "CANDIDATE" and old_p.confidence_score == 0.0:
                    if new_p.is_webcam_on:
                        new_p.confidence_score = 80.0
                        new_p.reasoning = f"Heuristic Match: Fast-tracked confidence based on immediate webcam state following the disconnection of historical candidate ({old_p.display_name})."
