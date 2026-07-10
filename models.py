import difflib

class ParticipantState:
    def __init__(self, participant_id: str, display_name: str):
        self.id = participant_id
        self.display_name = display_name
        self.is_webcam_on = False
        self.total_speaking_time = 0.0
        self.transcript_buffer = []
        self.role_verdict = "UNKNOWN"
        self.confidence_score = 0.0
        self.reasoning = "Just initialized."

    def calculate_base_name_score(self, target_candidate_name, interviewers_list):
        """Phase 1: Deterministic Fuzzy Matching"""
        # Clean string spaces and lower case
        name_clean = self.display_name.lower().strip()
        target_clean = target_candidate_name.lower().strip()
        
        # Check fuzzy ratio
        ratio = difflib.SequenceMatcher(None, name_clean, target_clean).ratio()
        if ratio > 0.85:
            self.confidence_score = 60.0
            self.reasoning = f"Display name '{self.display_name}' fuzzy matches metadata candidate name."
            return True
            
        # Check if they are explicitly an interviewer
        for interviewer in interviewers_list:
            if difflib.SequenceMatcher(None, name_clean, interviewer.lower().strip()).ratio() > 0.85:
                self.role_verdict = "INTERVIEWER"
                self.confidence_score = 0.0
                self.reasoning = f"Matched interviewer roster name: {interviewer}"
                return False
        return False
