import json
import time

def parse_time(ts_str):
    m, s = map(int, ts_str.split(':'))
    return m * 60 + s

def start_simulation(json_path, engine, speed_factor=10.0):
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    engine.initialize_metadata(data["external_metadata"])
    last_time = 0
    
    for event in data["timeline_events"]:
        curr_time = parse_time(event["timestamp"])
        delay = curr_time - last_time
        
        if delay > 0:
            time.sleep(delay / speed_factor)
            
        engine.process_event(event)
        print_live_dashboard(event["timestamp"], engine)
        last_time = curr_time

def print_live_dashboard(timestamp, engine):
    print(f"\n======== STREAM MONITOR [TIME: {timestamp}] ========")
    for p_id, p in engine.participants.items():
        cam_status = "ON" if p.is_webcam_on else "OFF"
        print(f"Person ID: {p_id} | Name: {p.display_name:<15} | Cam: {cam_status} | Verdict: {p.role_verdict:<11} | Confidence: {p.confidence_score:5.1f}%")
        print(f"   ↳ System Reasoning: {p.reasoning}")
    print("==========================================================")
