# graphics.py
# Photorealistic Medical Clinic Simulation with Full Voice Dialog

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import sys
import threading
import numpy as np
import time
import queue as queue_module

# Optional imports
try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import winsound
except ImportError:
    winsound = None

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    from gtts import gTTS
    import pygame
    import io
    import tempfile
    import os
except ImportError:
    gTTS = None
    pygame = None

# -------------------- VOICE QUEUE SYSTEM --------------------
speech_queue = queue_module.Queue()
speech_thread_running = True
current_speaking = False
speech_lock = threading.Lock()

# Next Mode variable
next_mode = False

def speech_worker():
    """Background thread that processes speech sequentially"""
    global current_speaking, speech_thread_running
    
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except ImportError:
        pass
    
    while speech_thread_running:
        try:
            item = speech_queue.get(timeout=0.5)
            if item is None:
                break
            
            text, is_doctor = item
            
            with speech_lock:
                current_speaking = True
            
            try:
                # Check if text contains Amharic characters
                has_amharic = any(0x1200 <= ord(c) <= 0x137F for c in text)
                lang = 'am' if has_amharic else 'en'
                
                if gTTS and pygame:
                    # Use gTTS for better language support
                    tts = gTTS(text=text, lang=lang, slow=False)
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
                        temp_file = f.name
                    tts.save(temp_file)
                    
                    pygame.mixer.init()
                    pygame.mixer.music.load(temp_file)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)
                    pygame.mixer.music.stop()
                    pygame.mixer.quit()
                    
                    # Clean up temp file
                    try:
                        os.unlink(temp_file)
                    except:
                        pass
                elif pyttsx3:
                    engine = pyttsx3.init()
                    engine.setProperty('rate', 150)
                    engine.setProperty('volume', 0.9)
                    engine.say(text)
                    engine.runAndWait()
                    engine.stop()
                elif winsound:
                    winsound.Beep(800 if is_doctor else 600, 200)
                else:
                    print(f"[VOICE] {text}")
            except Exception as e:
                print(f"[TTS Error] {e}")
            
            with speech_lock:
                current_speaking = False
            
            speech_queue.task_done()
            time.sleep(0.3)
            
        except queue_module.Empty:
            continue
    
    try:
        import pythoncom
        pythoncom.CoUninitialize()
    except:
        pass

# Start speech worker thread
speech_thread = threading.Thread(target=speech_worker, daemon=True)
speech_thread.start()

# -------------------- MEDICINE INVENTORY SYSTEM --------------------
medicine_inventory = {
    'Paracetamol': {'stock': 150, 'price': 25.0, 'expiry': '2025-12', 'color': (0.9, 0.2, 0.2)},
    'Amoxicillin': {'stock': 85, 'price': 45.0, 'expiry': '2025-08', 'color': (0.2, 0.9, 0.2)},
    'Ibuprofen': {'stock': 120, 'price': 30.0, 'expiry': '2026-01', 'color': (0.2, 0.2, 0.9)},
    'Vitamin C': {'stock': 200, 'price': 15.0, 'expiry': '2026-03', 'color': (0.9, 0.9, 0.2)},
    'Aspirin': {'stock': 95, 'price': 20.0, 'expiry': '2025-10', 'color': (0.9, 0.5, 0.2)},
    'Omeprazole': {'stock': 60, 'price': 55.0, 'expiry': '2025-11', 'color': (0.5, 0.3, 0.8)},
    'Lisinopril': {'stock': 45, 'price': 75.0, 'expiry': '2025-09', 'color': (0.3, 0.7, 0.7)},
    'Metformin': {'stock': 110, 'price': 40.0, 'expiry': '2026-02', 'color': (0.7, 0.5, 0.3)},
}

# -------------------- PATIENT NAMES IN ORDER --------------------
patient_names = ['Kindu', 'Mastewal', 'Belaynesh', 'Siteru', 'Megbat', 'Alebachew']
next_patient_name_index = 0

# -------------------- Data & Settings --------------------
# MOVED DOCTOR POSITIONS MORE TO THE LEFT
doctor_positions = [-0.15, 0.05, 0.25]  # Changed from [0.15, 0.35, 0.55] - moved left
consultation_rooms = []
patients = []
queue = []
doctor_occupied = False
game_active = True
paused = False
speed_multiplier = 1.0
walk_anim = 0.0 
gesture_anim = 0.0
consultation_phase = 0

# Door Animation Variables
entry_door_angle = 0.0
exit_door_angle = 0.0
pharmacy_door_angle = 0.0

# Timer and spawning control
start_time = 0
spawning_allowed = True
consultation_active = False
current_patient_idx = -1

# Doctor examination animation
doctor_examination_phase = 0
doctor_examination_timer = 0

# Enhanced constants
HUMAN_HEIGHT = 0.85
HEAD_SIZE = 0.055
NECK_LENGTH = 0.04
SHOULDER_WIDTH = 0.12
ARM_LENGTH = 0.22
LEG_LENGTH = 0.35
PATIENT_SPEED = 0.007       
CONSULTATION_DURATION = 1200
WAITING_ROOM_DURATION = 180 
TREATMENT_DURATION = 120
CLEANING_DELAY = 120        
HITBOX_SENSITIVITY = 0.02  
PHARMACY_VISIT_DURATION = 180
GESTURE_SPEED = 0.1

# Voice display
voice_text = ""
voice_display_text = ""
voice_timer = 0
help_text = ""
help_timer = 0
last_voice_stage = None

# Background image texture
background_texture_id = None
background_image_path = r"C:\Users\User\Downloads\rrr.avif"
background_texture_loaded = False

# TTS
use_tts = False
doctor_engine = None
patient_engine = None

# Bilingual Dialogues (English + Amharic) - Full conversations
dialogues = {
    'head': {
        0: ("Tell me about your headache.", "ራስ ምታትህን ንገረኝ።", "It hurts a lot, doctor. I have a history of migraines.", "በጣም ያቃጥለኛል ዶክተር። የማይግሬን ታሪክ አለኝ።"),
        1: ("When did it start?", "መቼ ጀመረ?", "Started this morning. I was stressed at work.", "ዛሬ ጠዋት ጀመረ። በስራ ጭንቀት ውስጥ ነበርኩ።"),
        2: ("How bad is the pain on a scale of 1-10?", "ከ1-10 ደረጃ ህመሙ ምን ያህል ነው?", "It's a 7 out of 10. Similar to my usual migraines.", "ከአስር ሰባት ነው። እንደ ወትሮዬ ማይግሬን ነው።"),
        3: ("Take this prescription and get plenty of rest.", "ይህን ማዘዣ ውሰድ እና ብዙ እረፍት አድርግ።", "Thank you, doctor. I will follow your advice.", "አመሰግናለሁ ዶክተር። ምክርህን እከተላለሁ።")
    },
    'arm': {
        0: ("What happened to your arm?", "ክንድህ ምን ሆነ?", "I fell and hurt it. I have osteoporosis.", "ወድቄ ቆስሏል። ኦስቲዮፖሮሲስ አለብኝ።"),
        1: ("When did the injury occur?", "ቁስሉ መቼ ነው የደረሰው?", "Yesterday afternoon. I was walking outside.", "ትናንት ከሰዓት። ከቤት ውጭ እየተራመድኩ ነበር።"),
        2: ("Can you move your fingers?", "ጣቶችህን ማንቀሳቀስ ትችላለህ?", "It's painful but I can move them a little.", "ያቃጥላል ግን ትንሽ ማንቀሳቀስ እችላለሁ።"),
        3: ("Take this prescription and rest your arm.", "ይህን ማዘዣ ውሰድ እና ክንድህን አሳርፍ።", "Thank you, doctor. I will take care.", "አመሰግናለሁ ዶክተር። እንክብካቤ አደርጋለሁ።")
    },
    'leg': {
        0: ("Describe your leg pain.", "የእግር ህመምህን ግለጽ።", "It aches when I walk. I have arthritis.", "ስሄድ ያቃጥለኛል። አርትራይተስ አለብኝ።"),
        1: ("How did you injure it?", "እንዴት ቆስሏል?", "I twisted it playing sports at the park.", "ስፖርት ስጫወት በፓርኩ ጠማሁት።"),
        2: ("Any swelling or redness?", "እብጠት ወይም መቅላት አለ?", "Yes, it's a bit swollen and red.", "አዎ ትንሽ አብጧል እና ቀልጧል።"),
        3: ("Take this prescription and apply ice.", "ይህን ማዘዣ ውሰድ እና በረዶ አድርግ።", "Thank you, doctor. I appreciate your help.", "አመሰግናለሁ ዶክተር። እርዳታህ አመሰግናለሁ።")
    },
    'fever': {
        0: ("How high is your fever?", "ትኩሳትህ ምን ያህል ነው?", "It's 101 degrees. I feel very weak.", "101 ዲግሪ ነው። በጣም ደክሞኛል።"),
        1: ("When did it start?", "መቼ ጀመረ?", "Two days ago. I thought it would go away.", "ከሁለት ቀን በፊት። ይጠፋል ብዬ አሰብኩ።"),
        2: ("Any other symptoms like cough or sore throat?", "ሌላ ምልክት እንደ ሳል ወይም የጉሮሮ ህመም አለ?", "Yes, I'm also coughing and my throat hurts.", "አዎ ሳልም ይዞኛል እና ጉሮሮዬ ያቃጥላል።"),
        3: ("Take this prescription and drink plenty of fluids.", "ይህን ማዘዣ ውሰድ እና ብዙ ፈሳሽ ጠጣ።", "Thank you, doctor. I will rest at home.", "አመሰግናለሁ ዶክተር። ቤት ውስጥ አርፋለሁ።")
    },
    'cough': {
        0: ("How long have you been coughing?", "ምን ያህል ጊዜ ሲሳሉ ቆይተዋል?", "For a week now. It's getting worse.", "ከሳምንት ጀምሮ። እየባሰ ነው።"),
        1: ("Is it dry or productive?", "ደረቅ ነው ወይስ ምራቅ አለው?", "It's dry and persistent, especially at night.", "ደረቅ እና የማያቋርጥ ነው፣ በተለይ በሌሊት።"),
        2: ("Any chest pain or difficulty breathing?", "የደረት ህመም ወይም የመተንፈስ ችግር አለ?", "A little when I cough heavily.", "ሳል ስል በጣም ትንሽ።"),
        3: ("Take this prescription and use a humidifier.", "ይህን ማዘዣ ውሰድ እና እርጥበት ማገጃ ተጠቀም።", "Thank you, doctor. I will do as you say.", "አመሰግናለሁ ዶክተር። እንደምትለው አደርጋለሁ።")
    },
    'chest': {
        0: ("Describe your chest pain.", "የደረት ህመምህን ግለጽ።", "It's sharp and comes and goes. I'm worried.", "ሹል እና እየመጣ እየሄደ ነው። ተጨንቄአለሁ።"),
        1: ("When does it occur?", "መቼ ነው የሚከሰት?", "When I breathe deeply or exercise.", "ጥልቅ ትንፋሽ ስወስድ ወይም ስለምመት።"),
        2: ("Any shortness of breath or dizziness?", "የትንፋሽ እጥረት ወይም መፍዘዝ አለ?", "Yes, sometimes I feel dizzy too.", "አዎ አንዳንድ ጊዜ መፍዘዝ ይሰማኛል።"),
        3: ("Take this prescription and schedule a follow-up.", "ይህን ማዘዣ ውሰድ እና ቀጣይ ቀጠሮ ያዝ።", "Thank you, doctor. I'll make an appointment.", "አመሰግናለሁ ዶክተር። ቀጠሮ አዘጋጃለሁ።")
    },
    'stomach': {
        0: ("Describe your stomach pain.", "የሆድ ህመምህን ግለጽ።", "It hurts after eating. I feel bloated.", "ስበላ በኋላ ያቃጥለኛል። እብጠት ይሰማኛል።"),
        1: ("When did it start?", "መቼ ጀመረ?", "A few days ago after eating spicy food.", "ከጥቂት ቀን በፊት ቅመም ምግብ ከበላሁ በኋላ።"),
        2: ("Any nausea or vomiting?", "እንባ ወይም ማስታወክ አለህ?", "Yes, I feel nauseous sometimes.", "አዎ አንዳንድ ጊዜ እንባ ይሰማኛል።"),
        3: ("Take this prescription and avoid spicy foods.", "ይህን ማዘዣ ውሰድ እና ቅመም ምግቦችን ተወግድ።", "Thank you, doctor. I will change my diet.", "አመሰግናለሁ ዶክተር። አመጋገቤን እቀይራለሁ።")
    },
    'psychology': {
        0: ("What's been bothering you emotionally?", "በስሜት ምን እያስጨናነህ ነው?", "I've been feeling very angry and frustrated lately.", "በቅርብ ጊዜ በጣም እንባ እና ብስጭት ይሰማኛል።"),
        1: ("When did this start?", "መቼ ጀመረ?", "Recently, with work stress and family issues.", "በቅርቡ ከስራ ጭንቀት እና ከቤተሰብ ጉዳዮች ጋር።"),
        2: ("How does it affect your daily life?", "በዕለት ተዕለት ህይወትህ ላይ እንዴት ያሳድዳል?", "I get angry easily and can't focus at work.", "በቀላሉ እንባ እሆናለሁ እና በስራ ላይ ማተኮር አልችልም።"),
        3: ("Let's discuss therapy options and medication.", "የማከራከር ምክር እና መድሀኒት እንያ።", "Thank you, doctor. I'm ready to get help.", "አመሰግናለሁ ዶክተር። እርዳታ ለማግኘት ዝግጁ ነኝ።")
    }
}

# Color Palettes
SKIN_TONES = [
    (0.96, 0.82, 0.72), (0.88, 0.74, 0.62), (0.78, 0.62, 0.52),
    (0.68, 0.52, 0.42), (0.58, 0.42, 0.32), (0.48, 0.32, 0.22)
]

HAIR_COLORS = [
    (0.08, 0.06, 0.05), (0.35, 0.25, 0.15), (0.55, 0.45, 0.30),
    (0.70, 0.60, 0.45), (0.85, 0.75, 0.55), (0.60, 0.40, 0.30)
]

EYE_COLORS = [
    (0.15, 0.12, 0.10), (0.35, 0.25, 0.15), (0.45, 0.65, 0.45),
    (0.35, 0.55, 0.85), (0.55, 0.45, 0.35)
]

PATIENT_GOWNS = [(0.75, 0.85, 0.95), (0.85, 0.95, 0.85), (0.95, 0.85, 0.75), (0.90, 0.90, 0.95)]
DOCTOR_SCRUBS = [(0.25, 0.55, 0.75), (0.30, 0.65, 0.45), (0.45, 0.45, 0.65)]

# Characters - DOCTOR MOVED MORE TO THE LEFT
doctor = {
    'x': -0.05, 'y': -0.25,  # Changed from 0.25 to -0.05 (moved left)
    'shirt_color': DOCTOR_SCRUBS[0],
    'pant_color': (0.20, 0.20, 0.25),
    'hair_color': HAIR_COLORS[1],
    'skin_tone': SKIN_TONES[0],
    'is_doctor': True,
    'examining': False,
    'blink_timer': 0,
    'is_blinking': False
}

receptionist = {
    'x': -0.15, 'y': -0.25,
    'shirt_color': (0.85, 0.85, 0.95),
    'pant_color': (0.15, 0.15, 0.30),
    'hair_color': HAIR_COLORS[3],
    'skin_tone': SKIN_TONES[2],
    'is_receptionist': True,
    'blink_timer': 0,
    'is_blinking': False
}

pharmacist = {
    'x': 1.38, 'y': -0.20,
    'shirt_color': (0.90, 0.90, 0.95),
    'pant_color': (0.18, 0.18, 0.28),
    'hair_color': HAIR_COLORS[2],
    'skin_tone': SKIN_TONES[3],
    'is_pharmacist': True,
    'blink_timer': 0,
    'is_blinking': False
}

# -------------------- HELPER FUNCTIONS --------------------
def reset_simulation():
    global patients, queue, doctor_occupied, consultation_rooms, game_active, start_time
    global consultation_active, current_patient_idx, doctor, voice_text, voice_display_text
    global voice_timer, last_voice_stage, medicine_inventory, spawning_allowed, next_patient_name_index
    
    game_active = True
    doctor_occupied = False
    consultation_active = False
    current_patient_idx = -1
    voice_text = ""
    voice_display_text = ""
    voice_timer = 0
    last_voice_stage = None
    queue = []
    spawning_allowed = True
    next_patient_name_index = 0
    
    consultation_rooms = [{'x': dx, 'status': 'clean', 'clean_timer': 0, 'room_number': i+1} 
                         for i, dx in enumerate(doctor_positions)]
    
    medicine_inventory = {
        'Paracetamol': {'stock': 150, 'price': 25.0, 'expiry': '2025-12', 'color': (0.9, 0.2, 0.2)},
        'Amoxicillin': {'stock': 85, 'price': 45.0, 'expiry': '2025-08', 'color': (0.2, 0.9, 0.2)},
        'Ibuprofen': {'stock': 120, 'price': 30.0, 'expiry': '2026-01', 'color': (0.2, 0.2, 0.9)},
        'Vitamin C': {'stock': 200, 'price': 15.0, 'expiry': '2026-03', 'color': (0.9, 0.9, 0.2)},
        'Aspirin': {'stock': 95, 'price': 20.0, 'expiry': '2025-10', 'color': (0.9, 0.5, 0.2)},
        'Omeprazole': {'stock': 60, 'price': 55.0, 'expiry': '2025-11', 'color': (0.5, 0.3, 0.8)},
        'Lisinopril': {'stock': 45, 'price': 75.0, 'expiry': '2025-09', 'color': (0.3, 0.7, 0.7)},
        'Metformin': {'stock': 110, 'price': 40.0, 'expiry': '2026-02', 'color': (0.7, 0.5, 0.3)},
    }
    
    patients = []
    for i in range(3):
        spawn_patient(i)
    
    start_time = glutGet(GLUT_ELAPSED_TIME)
    doctor['examining'] = False

def spawn_patient(i):
    global next_patient_name_index
    skin_tone = random.choice(SKIN_TONES)
    hair_color = random.choice(HAIR_COLORS)
    eye_color = random.choice(EYE_COLORS)
    
    # Get name in order
    patient_name = patient_names[next_patient_name_index % len(patient_names)]
    next_patient_name_index += 1
    
    # Assign specific conditions based on name
    if patient_name == 'Kindu':
        injury_type = 'head'
    elif patient_name == 'Belaynesh':
        injury_type = 'stomach'
    elif patient_name == 'Mastewal':
        injury_type = 'psychology'
    else:
        injury_type = random.choice(['arm', 'head', 'leg', 'fever', 'cough', 'chest', 'stomach', 'psychology'])
    
    patients.append({
        'id': i, 
        'x': -1.6 - (i * 0.4), 
        'y': -0.25,
        'name': patient_name,
        'shirt_color': random.choice(PATIENT_GOWNS),
        'pant_color': (0.20, 0.20, 0.28),
        'hair_color': hair_color,
        'skin_tone': skin_tone,
        'eye_color': eye_color,
        'has_prescription': False,
        'has_medicine': False,
        'state': 'walking_to_reception',
        'room_idx': -1,
        'treatment_timer': 0,
        'wait_timer': 0,
        'consultation_timer': 0,
        'pharmacy_timer': 0,
        'is_walking': False,
        'is_sitting': False,
        'injury_type': injury_type,
        'pain_level': random.randint(1, 10),
        'consultation_progress': 0,
        'prescribed_med': None,
        'blink_timer': 0,
        'is_blinking': False
    })

# -------------------- ADVANCE NEXT PATIENT FUNCTION --------------------
def advance_next_patient():
    """Advance the next patient to the next state (for Next Mode)"""
    global consultation_active, doctor_occupied, current_patient_idx, last_voice_stage
    
    for s in patients:
        if s['state'] not in ['walking_to_exit', 'leaving_pharmacy']:
            
            if s['state'] == 'walking_to_reception':
                s['x'] = -0.35
                s['state'] = 'in_queue'
                if s['id'] not in queue:
                    queue.append(s['id'])
                speak(f"{s['name']} moved to queue.")
                return
                
            elif s['state'] == 'in_queue':
                s['state'] = 'moving_to_receptionist'
                speak(f"{s['name']} moving to receptionist.")
                return
                
            elif s['state'] == 'moving_to_receptionist':
                s['x'] = receptionist['x'] - 0.08
                s['has_prescription'] = True
                s['state'] = 'walking_to_consultation'
                if queue and queue[0] == s['id']:
                    queue.pop(0)
                speak(f"{s['name']} going to consultation.")
                return
                
            elif s['state'] == 'walking_to_consultation':
                s['x'] = 0.05
                s['state'] = 'finding_room'
                return
                
            elif s['state'] == 'finding_room':
                for idx, r in enumerate(consultation_rooms):
                    if r['status'] == 'clean':
                        s['room_idx'] = idx
                        r['status'] = 'occupied'
                        s['state'] = 'moving_to_room'
                        break
                return
                
            elif s['state'] == 'moving_to_room':
                target = consultation_rooms[s['room_idx']]['x'] - 0.04
                s['x'] = target
                s['state'] = 'waiting_for_doctor'
                s['wait_timer'] = 1
                s['is_sitting'] = True
                return
                
            elif s['state'] == 'waiting_for_doctor':
                s['state'] = 'in_consultation'
                s['consultation_timer'] = 1
                consultation_active = True
                current_patient_idx = patients.index(s)
                doctor['examining'] = True
                return
                
            elif s['state'] == 'in_consultation':
                s['consultation_timer'] = 0
                prescriptions = {
                    'head': 'Paracetamol',
                    'arm': 'Ibuprofen',
                    'leg': 'Ibuprofen',
                    'fever': 'Aspirin',
                    'cough': 'Amoxicillin',
                    'chest': 'Vitamin C',
                    'stomach': 'Omeprazole',
                    'psychology': 'Vitamin C'
                }
                prescribed = prescriptions.get(s['injury_type'], 'Vitamin C')
                s['prescribed_med'] = prescribed
                update_medicine_stock(prescribed, 10)
                s['state'] = 'waiting_for_treatment'
                s['treatment_timer'] = 1
                consultation_active = False
                doctor['examining'] = False
                current_patient_idx = -1
                last_voice_stage = None
                return
                
            elif s['state'] == 'waiting_for_treatment':
                s['state'] = 'walking_to_pharmacy'
                s['is_sitting'] = False
                return
                
            elif s['state'] == 'walking_to_pharmacy':
                s['x'] = 1.38
                s['state'] = 'in_pharmacy'
                s['pharmacy_timer'] = 1
                return
                
            elif s['state'] == 'in_pharmacy':
                s['state'] = 'leaving_pharmacy'
                return
                
            elif s['state'] == 'leaving_pharmacy':
                s['x'] = 0.75
                s['state'] = 'walking_to_exit'
                s['is_sitting'] = False
                return
                
            elif s['state'] == 'walking_to_exit':
                s['x'] = 2.1
                return
    return

# -------------------- DRAWING FUNCTIONS --------------------
def rectangle(x1, y1, x2, y2, r, g, b, alpha=1.0):
    if alpha < 1.0:
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(r, g, b, alpha)
    else:
        glColor3f(r, g, b)
    glBegin(GL_QUADS)
    glVertex2f(x1, y1)
    glVertex2f(x2, y1)
    glVertex2f(x2, y2)
    glVertex2f(x1, y2)
    glEnd()
    if alpha < 1.0:
        glDisable(GL_BLEND)

def circle(cx, cy, radius, r, g, b, alpha=1.0):
    if alpha < 1.0:
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(r, g, b, alpha)
    else:
        glColor3f(r, g, b)
    glBegin(GL_POLYGON)
    for i in range(36):
        angle = 2 * math.pi * i / 36
        glVertex2f(cx + radius * math.cos(angle), cy + radius * math.sin(angle))
    glEnd()
    if alpha < 1.0:
        glDisable(GL_BLEND)

def draw_ellipse(cx, cy, rx, ry, r, g, b, alpha=1.0):
    if alpha < 1.0:
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(r, g, b, alpha)
    else:
        glColor3f(r, g, b)
    glBegin(GL_POLYGON)
    for i in range(36):
        angle = 2 * math.pi * i / 36
        glVertex2f(cx + rx * math.cos(angle), cy + ry * math.sin(angle))
    glEnd()
    if alpha < 1.0:
        glDisable(GL_BLEND)

def rounded_rect(x1, y1, x2, y2, r, g, b, radius=0.02):
    rectangle(x1 + radius, y1, x2 - radius, y2, r, g, b)
    rectangle(x1, y1 + radius, x2, y2 - radius, r, g, b)
    circle(x1 + radius, y1 + radius, radius, r, g, b)
    circle(x2 - radius, y1 + radius, radius, r, g, b)
    circle(x1 + radius, y2 - radius, radius, r, g, b)
    circle(x2 - radius, y2 - radius, radius, r, g, b)

def draw_limb(x1, y1, x2, y2, r, g, b, thickness=0.03):
    angle = math.atan2(y2 - y1, x2 - x1)
    perp_x = -math.sin(angle) * thickness
    perp_y = math.cos(angle) * thickness
    glColor3f(r, g, b)
    glBegin(GL_QUADS)
    glVertex2f(x1 + perp_x, y1 + perp_y)
    glVertex2f(x1 - perp_x, y1 - perp_y)
    glVertex2f(x2 - perp_x, y2 - perp_y)
    glVertex2f(x2 + perp_x, y2 + perp_y)
    glEnd()
    circle(x1, y1, thickness * 0.8, r, g, b)
    circle(x2, y2, thickness * 0.7, r, g, b)

def draw_realistic_human(s_data, is_doctor=False, is_pharmacist=False, is_receptionist=False):
    x, y = s_data['x'], s_data['y']
    is_walking = s_data.get('is_walking', False)
    state = s_data.get('state', '')
    skin = s_data.get('skin_tone', SKIN_TONES[0])
    eye_color = s_data.get('eye_color', EYE_COLORS[0])
    hair_color = s_data.get('hair_color', HAIR_COLORS[0])
    
    global gesture_anim, walk_anim
    
    walk_swing = math.sin(walk_anim * 10) * 0.03 if is_walking else 0
    is_sitting = state in ['waiting_for_doctor', 'in_consultation', 'waiting_for_treatment', 'in_pharmacy']
    
    if is_sitting:
        hip_y = y + 0.05
        shoulder_y = hip_y + 0.28
    else:
        hip_y = y + 0.20
        shoulder_y = hip_y + 0.35
    
    # Legs
    if not is_sitting:
        leg_x_offset = walk_swing * 0.5
        draw_limb(x - 0.035 + leg_x_offset, hip_y, x - 0.04 + leg_x_offset, y - 0.10, *s_data['pant_color'], thickness=0.04)
        draw_limb(x + 0.035 - leg_x_offset, hip_y, x + 0.04 - leg_x_offset, y - 0.10, *s_data['pant_color'], thickness=0.04)
    
    # Torso
    for i in range(3):
        shade = 0.7 + i * 0.15
        x_offset = (i - 1) * 0.01
        rounded_rect(x - 0.07 + x_offset, hip_y, x + 0.07 + x_offset, shoulder_y,
                    s_data['shirt_color'][0] * shade, s_data['shirt_color'][1] * shade, s_data['shirt_color'][2] * shade, radius=0.025)
    
    # Doctor's coat
    if is_doctor:
        rounded_rect(x - 0.08, hip_y, x + 0.08, shoulder_y, 0.95, 0.95, 0.98, radius=0.025)
        glColor3f(0.7, 0.7, 0.75)
        glLineWidth(2)
        glBegin(GL_LINES)
        glVertex2f(x, hip_y + 0.05)
        glVertex2f(x, shoulder_y - 0.05)
        glEnd()
    
    # Arms
    arm_swing = walk_swing * 1.2 if is_walking else 0
    
    if is_doctor and consultation_active:
        gesture_offset = math.sin(gesture_anim * 3) * 0.02
        draw_limb(x - 0.09 - gesture_offset, shoulder_y - 0.05, x - 0.13 - gesture_offset, shoulder_y - 0.25, *s_data['shirt_color'], thickness=0.035)
        draw_limb(x + 0.09 + gesture_offset, shoulder_y - 0.05, x + 0.13 + gesture_offset, shoulder_y - 0.20, *s_data['shirt_color'], thickness=0.035)
        draw_stethoscope(x + 0.12, shoulder_y - 0.15, gesture_anim)
    else:
        draw_limb(x - 0.09 - arm_swing, shoulder_y - 0.05, x - 0.12 - arm_swing, shoulder_y - 0.28, *s_data['shirt_color'], thickness=0.035)
        draw_limb(x + 0.09 + arm_swing, shoulder_y - 0.05, x + 0.12 + arm_swing, shoulder_y - 0.28, *s_data['shirt_color'], thickness=0.035)
    
    # Neck and Head
    neck_y = shoulder_y + 0.02
    rectangle(x - 0.025, shoulder_y, x + 0.025, neck_y, skin[0]*0.8, skin[1]*0.7, skin[2]*0.6)
    head_y = neck_y + 0.06
    head_size = HEAD_SIZE
    draw_ellipse(x, head_y, head_size, head_size * 1.05, *skin)
    
    # Hair
    if hair_color[0] < 0.3:
        draw_ellipse(x, head_y + 0.02, head_size * 0.85, head_size * 0.55, *hair_color)
        draw_ellipse(x - head_size * 0.65, head_y - 0.01, head_size * 0.3, head_size * 0.5, *hair_color)
        draw_ellipse(x + head_size * 0.65, head_y - 0.01, head_size * 0.3, head_size * 0.5, *hair_color)
    else:
        for i in range(3):
            offset = (i - 1) * 0.015
            draw_ellipse(x + offset, head_y + 0.02, head_size * 0.5, head_size * 0.35, *hair_color)
    
    # Eyes
    blink = s_data.get('is_blinking', False)
    eye_left_x = x - 0.018
    eye_right_x = x + 0.018
    eye_y = head_y + 0.01
    
    circle(eye_left_x, eye_y, 0.009, 1.0, 1.0, 1.0)
    circle(eye_right_x, eye_y, 0.009, 1.0, 1.0, 1.0)
    circle(eye_left_x, eye_y, 0.005, *eye_color)
    circle(eye_right_x, eye_y, 0.005, *eye_color)
    circle(eye_left_x, eye_y, 0.0025, 0.05, 0.05, 0.05)
    circle(eye_right_x, eye_y, 0.0025, 0.05, 0.05, 0.05)
    circle(eye_left_x - 0.002, eye_y + 0.002, 0.0015, 1.0, 1.0, 1.0)
    circle(eye_right_x - 0.002, eye_y + 0.002, 0.0015, 1.0, 1.0, 1.0)
    
    if blink:
        rectangle(eye_left_x - 0.01, eye_y - 0.002, eye_left_x + 0.01, eye_y + 0.006, *skin)
        rectangle(eye_right_x - 0.01, eye_y - 0.002, eye_right_x + 0.01, eye_y + 0.006, *skin)
    
    # Eyebrows
    glColor3f(hair_color[0], hair_color[1], hair_color[2])
    glLineWidth(3)
    glBegin(GL_LINES)
    glVertex2f(eye_left_x - 0.012, eye_y + 0.012)
    glVertex2f(eye_left_x + 0.008, eye_y + 0.014)
    glVertex2f(eye_right_x - 0.008, eye_y + 0.014)
    glVertex2f(eye_right_x + 0.012, eye_y + 0.012)
    glEnd()
    
    # Nose
    glColor3f(skin[0]*0.85, skin[1]*0.75, skin[2]*0.7)
    glBegin(GL_TRIANGLES)
    glVertex2f(x, eye_y - 0.005)
    glVertex2f(x - 0.008, eye_y - 0.018)
    glVertex2f(x + 0.008, eye_y - 0.018)
    glEnd()
    
    # Mouth
    glBegin(GL_LINE_STRIP)
    glVertex2f(x - 0.012, head_y - 0.022)
    glVertex2f(x, head_y - 0.020)
    glVertex2f(x + 0.012, head_y - 0.022)
    glEnd()
    
    # Ears
    draw_ellipse(x - head_size * 0.85, head_y, head_size * 0.25, head_size * 0.35, *skin)
    draw_ellipse(x + head_size * 0.85, head_y, head_size * 0.25, head_size * 0.35, *skin)
    
    # Medical equipment
    if is_doctor:
        rectangle(x - 0.03, shoulder_y - 0.08, x + 0.03, shoulder_y - 0.05, 1.0, 1.0, 1.0, 0.9)
        rectangle(x - 0.025, shoulder_y - 0.075, x + 0.025, shoulder_y - 0.055, 0.2, 0.4, 0.8, 0.9)
    elif is_pharmacist:
        rectangle(x - 0.07, hip_y + 0.05, x + 0.07, shoulder_y - 0.05, 0.9, 0.95, 1.0, 0.7)
    elif is_receptionist:
        rectangle(x - 0.02, shoulder_y - 0.07, x + 0.02, shoulder_y - 0.05, 0.9, 0.9, 0.9, 0.9)
    
    # Injury indicators
    if not is_doctor and not is_pharmacist and not is_receptionist:
        if s_data.get('injury_type') == 'arm':
            rectangle(x - 0.13, shoulder_y - 0.20, x - 0.09, shoulder_y - 0.16, 0.95, 0.92, 0.88, 0.9)
        elif s_data.get('injury_type') == 'head':
            rectangle(x - 0.04, head_y + 0.005, x + 0.04, head_y + 0.025, 0.95, 0.92, 0.88, 0.8)
        elif s_data.get('injury_type') == 'leg':
            rectangle(x - 0.045, hip_y - 0.10, x - 0.025, hip_y + 0.05, 0.95, 0.92, 0.88, 0.8)

def draw_stethoscope(x, y, angle=0):
    glColor3f(0.35, 0.35, 0.40)
    glLineWidth(3)
    glBegin(GL_LINE_STRIP)
    for i in range(20):
        t = i / 20.0
        px = x - 0.05 * t
        py = y + 0.02 * math.sin(t * math.pi)
        glVertex2f(px, py)
    glEnd()
    circle(x - 0.07, y + 0.03, 0.008, 0.45, 0.45, 0.50)
    circle(x - 0.05, y + 0.03, 0.008, 0.45, 0.45, 0.50)
    circle(x, y, 0.015, 0.55, 0.55, 0.60)
    circle(x, y, 0.010, 0.70, 0.70, 0.75)

def draw_pill_bottle(x, y):
    rounded_rect(x - 0.025, y, x + 0.025, y + 0.08, 0.85, 0.85, 0.90, radius=0.01)
    rectangle(x - 0.022, y + 0.08, x + 0.022, y + 0.09, 0.75, 0.70, 0.65)
    rectangle(x - 0.02, y + 0.03, x + 0.02, y + 0.06, 0.95, 0.95, 1.00)
    circle(x - 0.008, y + 0.045, 0.005, 1.0, 0.3, 0.3, 0.7)
    circle(x + 0.008, y + 0.055, 0.005, 1.0, 0.3, 0.3, 0.7)

def draw_medicine_shelf(x, y, width, height):
    rounded_rect(x, y, x + width, y + height, 0.45, 0.35, 0.25, radius=0.01)
    shelf_height = height / 4
    for i in range(4):
        shelf_y = y + (i + 1) * shelf_height
        rectangle(x, shelf_y - 0.015, x + width, shelf_y + 0.015, 0.55, 0.45, 0.35)
    
    med_items = list(medicine_inventory.items())
    for idx, (med_name, data) in enumerate(med_items[:8]):
        col = idx % 4
        row = idx // 4
        med_x = x + 0.035 + col * (width / 4)
        med_y = y + height - 0.08 - row * (height / 4)
        draw_pill_bottle(med_x, med_y)

def draw_medicine_stock_display():
    rectangle(1.25, 0.35, 1.95, 0.68, 0.12, 0.12, 0.15, 0.85)
    rectangle(1.27, 0.37, 1.93, 0.66, 0.08, 0.08, 0.10, 0.95)
    draw_text(1.35, 0.62, "MEDICINE INVENTORY", GLUT_BITMAP_HELVETICA_18, 1.0, 0.9, 0.2)
    
    y_offset = 0.58
    for idx, (med_name, data) in enumerate(list(medicine_inventory.items())[:6]):
        y_pos = y_offset - (idx + 1) * 0.038
        draw_text(1.3, y_pos, f"{med_name[:12]}:", GLUT_BITMAP_HELVETICA_12, 0.85, 0.85, 0.85)
        if data['stock'] < 20:
            draw_text(1.58, y_pos, f"{data['stock']}", GLUT_BITMAP_HELVETICA_12, 1.0, 0.3, 0.3)
        elif data['stock'] < 50:
            draw_text(1.58, y_pos, f"{data['stock']}", GLUT_BITMAP_HELVETICA_12, 1.0, 0.8, 0.2)
        else:
            draw_text(1.58, y_pos, f"{data['stock']}", GLUT_BITMAP_HELVETICA_12, 0.3, 1.0, 0.3)

def draw_queue_display():
    rectangle(-1.9, 0.55, -1.0, 0.75, 0.12, 0.12, 0.15, 0.85)
    rectangle(-1.88, 0.57, -1.02, 0.73, 0.08, 0.08, 0.10, 0.95)
    draw_text(-1.85, 0.70, "PATIENT QUEUE", GLUT_BITMAP_HELVETICA_18, 1.0, 0.9, 0.2)
    draw_text(-1.85, 0.66, f"Waiting: {len(queue)}", GLUT_BITMAP_HELVETICA_12, 0.85, 0.85, 0.85)
    
    for idx, patient_id in enumerate(queue[:5]):
        y_pos = 0.63 - idx * 0.03
        for p in patients:
            if p['id'] == patient_id:
                draw_text(-1.85, y_pos, f"{idx+1}. {p['name']} - {p['injury_type']} (Pain: {p['pain_level']}/10)", 
                         GLUT_BITMAP_HELVETICA_12, 0.7, 0.85, 1.0)
                break

def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18, r=1.0, g=1.0, b=1.0):
    glColor3f(r, g, b)
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))

def draw_control_panel():
    """Draw the control panel on screen"""
    # Control panel background
    rectangle(-1.9, -0.75, -0.5, -0.4, 0.0, 0.0, 0.0, 0.85)
    rectangle(-1.88, -0.73, -0.52, -0.42, 0.1, 0.1, 0.15, 0.95)
    
    # Title
    draw_text(-1.85, -0.44, "CONTROLS", GLUT_BITMAP_HELVETICA_18, 1.0, 0.9, 0.2)
    
    # Control buttons
    controls = [
        ("R", "Reset Simulation"),
        ("O", "Open Doors"),
        ("P", "Pause/Resume"),
        ("S", "Spawn Patient"),
        ("F", "Increase Speed"),
        ("N", "Next Mode ON/OFF"),
        ("SPACE", "Advance (Next Mode)"),
        ("H", "Help"),
        ("1-6", "Adjust Settings"),
        ("Q/ESC", "Quit")
    ]
    
    y_start = -0.48
    for i, (key, desc) in enumerate(controls):
        y_pos = y_start - (i * 0.03)
        draw_text(-1.85, y_pos, f"{key}:", GLUT_BITMAP_HELVETICA_12, 0.3, 1.0, 0.3)
        draw_text(-1.65, y_pos, desc, GLUT_BITMAP_HELVETICA_12, 0.85, 0.85, 0.85)

def draw_status_panel():
    """Draw status panel showing current simulation info"""
    # Status panel background
    rectangle(1.0, -0.75, 1.95, -0.3, 0.0, 0.0, 0.0, 0.85)
    rectangle(1.02, -0.73, 1.93, -0.32, 0.1, 0.1, 0.15, 0.95)
    
    # Title
    draw_text(1.05, -0.34, "STATUS", GLUT_BITMAP_HELVETICA_18, 1.0, 0.9, 0.2)
    
    # Status info
    y_start = -0.38
    status_items = [
        f"Speed: {speed_multiplier}x",
        f"Paused: {'YES' if paused else 'NO'}",
        f"Next Mode: {'ON' if next_mode else 'OFF'}",
        f"Patients: {len(patients)}",
        f"Queue: {len(queue)}",
        f"Consultation: {'Active' if consultation_active else 'Inactive'}"
    ]
    
    for i, item in enumerate(status_items):
        y_pos = y_start - (i * 0.03)
        draw_text(1.05, y_pos, item, GLUT_BITMAP_HELVETICA_12, 0.85, 0.85, 0.85)

# -------------------- VOICE FUNCTIONS --------------------
def init_tts():
    global use_tts, doctor_engine, patient_engine
    if not pyttsx3:
        print("[TTS] pyttsx3 not installed")
        return
    try:
        test_engine = pyttsx3.init()
        voices = test_engine.getProperty('voices')
        print(f"[TTS] Available voices: {len(voices)}")
        for v in voices:
            print(f"  - {v.name}")
        
        doctor_engine = pyttsx3.init()
        patient_engine = pyttsx3.init()
        
        if len(voices) > 0:
            doctor_engine.setProperty('voice', voices[0].id)
        if len(voices) > 1:
            patient_engine.setProperty('voice', voices[1].id)
        
        doctor_engine.setProperty('rate', 150)
        doctor_engine.setProperty('volume', 0.9)
        patient_engine.setProperty('rate', 150)
        patient_engine.setProperty('volume', 0.9)
        
        test_engine.stop()
        use_tts = True
        print("[TTS] Voice system initialized!")
    except Exception as e:
        print(f"[TTS] Failed: {e}")
        use_tts = False

def speak(text, display_text=None, is_doctor=False):
    global voice_text, voice_display_text, voice_timer
    voice_text = text
    voice_display_text = display_text or text
    voice_timer = 180
    
    speech_queue.put((text, is_doctor))
    print(f"{'👨‍⚕️ Doctor' if is_doctor else '🧑‍🦱 Patient'}: {text}")

def update_blinking(human):
    if human.get('blink_timer', 0) <= 0:
        if random.random() < 0.005:
            human['is_blinking'] = True
            human['blink_timer'] = 5
    else:
        human['blink_timer'] -= 1
        if human['blink_timer'] <= 0:
            human['is_blinking'] = False

def update_medicine_stock(med_name, quantity):
    global medicine_inventory
    if med_name in medicine_inventory:
        medicine_inventory[med_name]['stock'] -= quantity
        if medicine_inventory[med_name]['stock'] < 0:
            medicine_inventory[med_name]['stock'] = 0
        return True
    return False

# -------------------- ENVIRONMENT DRAWING --------------------
def draw_animated_door(x, y, angle, r, g, b):
    rectangle(x - 0.02, y, x + 0.1, y + 0.37, 0.35, 0.25, 0.18)
    swing_width = 0.09 * math.cos(math.radians(angle))
    rectangle(x, y + 0.01, x + swing_width, y + 0.35, r, g, b)
    circle(x + swing_width - 0.015, y + 0.17, 0.012, 0.9, 0.85, 0.7)

def draw_medical_symbol(x, y):
    rectangle(x - 0.03, y - 0.02, x + 0.03, y + 0.02, 1.0, 0.2, 0.2, 0.9)
    rectangle(x - 0.02, y - 0.03, x + 0.02, y + 0.03, 1.0, 0.2, 0.2, 0.8)

def draw_pharmacy_symbol(x, y):
    draw_ellipse(x, y, 0.045, 0.02, 0.0, 0.7, 0.0, 0.8)

def draw_modern_window(x, y, width, height):
    rectangle(x, y, x + width, y + height, 0.35, 0.35, 0.40, 0.9)
    rectangle(x + 0.02, y + 0.02, x + width - 0.02, y + height - 0.02, 0.65, 0.8, 0.95, 0.7)

def draw_modern_building(x1, y1, x2, y2, base_color, roof_color):
    for i in range(8):
        y_start = y1 + (y2 - y1) * i / 8
        y_end = y1 + (y2 - y1) * (i + 1) / 8
        shade = 0.6 + 0.4 * (i / 8)
        rectangle(x1, y_start, x2, y_end, base_color[0] * shade, base_color[1] * shade, base_color[2] * shade)
    glColor3f(*roof_color)
    glBegin(GL_TRIANGLES)
    glVertex2f(x1 - 0.03, y2)
    glVertex2f(x2 + 0.03, y2)
    glVertex2f((x1 + x2) / 2, y2 + 0.18)
    glEnd()

def draw_tree(x, y):
    rectangle(x - 0.035, y, x + 0.035, y + 0.35, 0.5, 0.35, 0.2)
    circle(x, y + 0.38, 0.12, 0.1, 0.6, 0.1)
    circle(x - 0.07, y + 0.32, 0.09, 0.15, 0.65, 0.15)
    circle(x + 0.07, y + 0.32, 0.09, 0.15, 0.65, 0.15)
    circle(x, y + 0.48, 0.09, 0.12, 0.62, 0.12)

def draw_house(x, y):
    rectangle(x - 0.18, y, x + 0.18, y + 0.28, 0.85, 0.7, 0.5)
    glColor3f(0.65, 0.4, 0.25)
    glBegin(GL_TRIANGLES)
    glVertex2f(x - 0.22, y + 0.28)
    glVertex2f(x + 0.22, y + 0.28)
    glVertex2f(x, y + 0.48)
    glEnd()
    rectangle(x - 0.04, y, x + 0.04, y + 0.12, 0.45, 0.3, 0.2)

def draw_patient_chair(x, y):
    rectangle(x - 0.045, y, x + 0.045, y + 0.025, 0.55, 0.45, 0.35)
    rectangle(x - 0.045, y + 0.025, x + 0.045, y + 0.14, 0.6, 0.5, 0.4)
    rectangle(x - 0.04, y - 0.06, x - 0.025, y, 0.5, 0.4, 0.3)
    rectangle(x + 0.025, y - 0.06, x + 0.04, y, 0.5, 0.4, 0.3)
    rectangle(x - 0.045, y + 0.14, x + 0.045, y + 0.22, 0.55, 0.45, 0.35, 0.8)

def draw_patient_bed(x, y):
    rectangle(x - 0.09, y - 0.025, x + 0.09, y, 0.45, 0.35, 0.25)
    rectangle(x - 0.08, y, x + 0.08, y + 0.04, 0.9, 0.85, 0.8)
    rectangle(x - 0.09, y + 0.04, x + 0.09, y + 0.09, 0.55, 0.45, 0.35)
    rectangle(x - 0.05, y + 0.04, x + 0.05, y + 0.07, 0.85, 0.8, 0.75)

def draw_ambulance(x, y):
    rectangle(x - 0.2, y - 0.06, x + 0.2, y + 0.1, 1.0, 1.0, 1.0, 0.9)
    circle(x - 0.12, y - 0.1, 0.04, 0.25, 0.25, 0.25, 0.9)
    circle(x + 0.12, y - 0.1, 0.04, 0.25, 0.25, 0.25, 0.9)
    rectangle(x - 0.05, y + 0.06, x - 0.02, y + 0.09, 1.0, 0.0, 0.0, 0.9)
    rectangle(x - 0.035, y + 0.045, x - 0.035, y + 0.105, 1.0, 0.0, 0.0, 0.9)

def draw_normal_ambulance(x, y):
    rectangle(x - 0.17, y - 0.06, x + 0.17, y + 0.1, 1.0, 1.0, 1.0, 0.9)
    circle(x - 0.09, y - 0.1, 0.035, 0.25, 0.25, 0.25, 0.9)
    circle(x + 0.09, y - 0.1, 0.035, 0.25, 0.25, 0.25, 0.9)

def load_background_texture(path):
    global background_texture_id, background_texture_loaded
    if Image is None:
        return
    try:
        image = Image.open(path)
        image = image.convert('RGBA')
        width, height = image.size
        image_data = image.tobytes('raw', 'RGBA', 0, -1)
        background_texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, background_texture_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, image_data)
        glBindTexture(GL_TEXTURE_2D, 0)
        background_texture_loaded = True
    except Exception as e:
        print(f"Failed to load background: {e}")

def draw_background_image():
    global background_texture_loaded, background_texture_id
    if not background_texture_loaded or background_texture_id is None:
        return
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, background_texture_id)
    glColor3f(1.0, 1.0, 1.0)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex2f(-2.0, -0.8)
    glTexCoord2f(1.0, 0.0); glVertex2f(2.5, -0.8)
    glTexCoord2f(1.0, 1.0); glVertex2f(2.5, 0.8)
    glTexCoord2f(0.0, 1.0); glVertex2f(-2.0, 0.8)
    glEnd()
    glBindTexture(GL_TEXTURE_2D, 0)
    glDisable(GL_TEXTURE_2D)

# -------------------- MAIN DISPLAY --------------------
def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    draw_background_image()
    
    # Sky gradient
    glBegin(GL_QUADS)
    glColor3f(0.55, 0.75, 0.95); glVertex2f(-2.0, 0.8)
    glColor3f(0.45, 0.65, 0.85); glVertex2f(2.5, 0.8)
    glColor3f(0.35, 0.55, 0.75); glVertex2f(2.5, -0.8)
    glColor3f(0.25, 0.45, 0.65); glVertex2f(-2.0, -0.8)
    glEnd()
    
    # Ground
    glBegin(GL_QUADS)
    glColor3f(0.35, 0.55, 0.35); glVertex2f(-2.0, -0.25)
    glColor3f(0.45, 0.65, 0.45); glVertex2f(2.5, -0.25)
    glColor3f(0.35, 0.55, 0.35); glVertex2f(2.5, -0.8)
    glColor3f(0.25, 0.45, 0.25); glVertex2f(-2.0, -0.8)
    glEnd()
    
    # Path
    glBegin(GL_QUADS)
    glColor3f(0.5, 0.5, 0.5); glVertex2f(-2.0, -0.25)
    glColor3f(0.6, 0.6, 0.6); glVertex2f(2.5, -0.25)
    glColor3f(0.5, 0.5, 0.5); glVertex2f(2.5, -0.18)
    glColor3f(0.4, 0.4, 0.4); glVertex2f(-2.0, -0.18)
    glEnd()
    
    # Buildings
    draw_modern_building(-0.95, -0.2, -0.05, 0.6, (0.75, 0.75, 0.85), (0.65, 0.65, 0.75))
    rectangle(-0.25, -0.2, -0.05, 0.05, 0.55, 0.55, 0.65)
    draw_modern_building(0.05, -0.2, 0.85, 0.6, (0.85, 0.85, 0.95), (0.75, 0.75, 0.85))
    draw_modern_building(0.9, -0.2, 1.75, 0.6, (0.8, 0.85, 0.9), (0.7, 0.75, 0.8))
    
    # Doors
    draw_animated_door(-0.93, -0.2, entry_door_angle, 0.6, 0.6, 0.7)
    draw_animated_door(1.66, -0.2, exit_door_angle, 0.6, 0.6, 0.7)
    draw_animated_door(1.25, -0.2, pharmacy_door_angle, 0.65, 0.65, 0.75)
    
    # Windows
    draw_modern_window(-0.8, 0.1, 0.15, 0.15)
    draw_modern_window(-0.5, 0.1, 0.15, 0.15)
    draw_modern_window(-0.2, 0.1, 0.15, 0.15)
    draw_modern_window(0.3, 0.1, 0.15, 0.15)
    draw_modern_window(0.6, 0.1, 0.15, 0.15)
    draw_modern_window(1.05, 0.1, 0.15, 0.15)
    draw_modern_window(1.35, 0.1, 0.15, 0.15)
    
    # Pharmacy area
    rectangle(1.3, -0.15, 1.46, 0.2, 0.45, 0.35, 0.25, 0.9)
    rectangle(1.32, -0.1, 1.44, 0.15, 0.55, 0.45, 0.35, 0.85)
    
    draw_medicine_shelf(1.48, -0.15, 0.28, 0.48)
    draw_medicine_stock_display()
    
    # Consultation rooms
    for r in consultation_rooms:
        rectangle(r['x'] - 0.14, -0.2, r['x'] + 0.14, -0.05, 0.45, 0.45, 0.55, 0.7)
        rectangle(r['x'] - 0.12, -0.05, r['x'] + 0.12, -0.02, 0.65, 0.65, 0.75, 0.9)
        draw_patient_chair(r['x'] - 0.06, -0.15)
        draw_patient_bed(r['x'] + 0.03, -0.15)
        
        if r['status'] == 'occupied':
            draw_stethoscope(r['x'], 0.05)
        elif r['status'] == 'dirty':
            rectangle(r['x'] - 0.025, 0.03, r['x'] + 0.025, 0.07, 1.0, 0.85, 0.2, 0.8)
    
    # Medical symbols
    draw_medical_symbol(-0.5, 0.45)
    draw_medical_symbol(0.6, 0.45)
    draw_pharmacy_symbol(1.4, 0.45)
    
    # Sign
    rectangle(-0.7, 0.5, -0.3, 0.6, 0.95, 0.95, 0.95, 0.9)
    draw_text(-0.67, 0.53, "MEDICAL", GLUT_BITMAP_HELVETICA_12, 0.8, 0.2, 0.2)
    draw_text(-0.65, 0.57, "CLINIC", GLUT_BITMAP_HELVETICA_12, 0.2, 0.5, 0.8)
    
    # Trees and house
    draw_tree(-1.25, -0.2)
    draw_tree(2.15, -0.2)
    draw_tree(-1.8, -0.2)
    draw_house(-1.6, -0.2)
    
    # Ambulances
    draw_normal_ambulance(-2.0, -0.25)
    draw_ambulance(2.5, -0.25)
    
    # Patient seating
    draw_patient_chair(-0.8, -0.15)
    draw_patient_chair(-0.6, -0.15)
    draw_patient_chair(-0.4, -0.15)
    draw_patient_chair(0.9, -0.15)
    draw_patient_chair(1.1, -0.15)
    draw_patient_bed(-0.4, 0.0)
    draw_patient_bed(0.3, 0.0)
    draw_patient_bed(0.7, 0.0)
    
    # Queue display
    draw_queue_display()
    
    # Draw Control Panel and Status Panel
    draw_control_panel()
    draw_status_panel()
    
    # Draw all humans
    update_blinking(doctor)
    update_blinking(receptionist)
    update_blinking(pharmacist)
    
    draw_realistic_human(receptionist, is_receptionist=True)
    draw_realistic_human(doctor, is_doctor=True)
    draw_realistic_human(pharmacist, is_pharmacist=True)
    
    for s in patients:
        update_blinking(s)
        draw_realistic_human(s)
    
    # Voice text overlay
    if voice_timer > 0 and voice_display_text:
        rectangle(-1.5, 0.65, 1.3, 0.8, 0.0, 0.0, 0.0, 0.7)
        draw_text(-1.45, 0.69, voice_display_text[:50], GLUT_BITMAP_HELVETICA_12, 1.0, 1.0, 0.8)
    
    # Help text overlay
    if help_timer > 0 and help_text:
        rectangle(-1.5, 0.5, 1.3, 0.65, 0.0, 0.0, 0.0, 0.7)
        draw_text(-1.45, 0.53, help_text[:50], GLUT_BITMAP_HELVETICA_12, 1.0, 1.0, 0.8)
    
    # Next mode indicator
    if next_mode:
        rectangle(-1.5, 0.35, -0.5, 0.48, 0.0, 0.5, 0.0, 0.7)
        draw_text(-1.45, 0.38, "NEXT MODE: ON (Press SPACE)", GLUT_BITMAP_HELVETICA_12, 0.0, 1.0, 0.0)
    
    glutSwapBuffers()

# -------------------- UPDATE LOGIC --------------------
def update(value):
    global walk_anim, gesture_anim, doctor_occupied, consultation_active, current_patient_idx
    global entry_door_angle, exit_door_angle, pharmacy_door_angle, spawning_allowed
    global voice_timer, voice_text, voice_display_text, last_voice_stage, help_timer
    
    if not game_active or paused:
        glutTimerFunc(16, update, 0)
        return
    
    walk_anim += 0.02 * speed_multiplier
    gesture_anim += GESTURE_SPEED * speed_multiplier
    
    if voice_timer > 0:
        voice_timer -= speed_multiplier
        if voice_timer <= 0:
            voice_text = ""
            voice_display_text = ""
    
    if help_timer > 0:
        help_timer -= speed_multiplier
    
    if consultation_active and current_patient_idx >= 0 and current_patient_idx < len(patients):
        patients[current_patient_idx]['consultation_progress'] += speed_multiplier
        progress = patients[current_patient_idx]['consultation_progress']
        stage = min(3, int((progress * 4) // CONSULTATION_DURATION))
        doctor['consultation_stage'] = stage
        
        if stage != last_voice_stage and stage <= 3:
            last_voice_stage = stage
            injury = patients[current_patient_idx]['injury_type']
            doctor_line, doctor_amharic, patient_line, patient_amharic = dialogues[injury][stage]
            
            # Speak doctor line with delay
            speak(doctor_line, f"{doctor_line}\n{doctor_amharic}", is_doctor=True)
            
            # Speak patient response after delay
            glutTimerFunc(2500, lambda v, pl=patient_line, pa=patient_amharic: 
                         speak(pl, f"{pl}\n{pa}", is_doctor=False), 0)
    
    current_time = glutGet(GLUT_ELAPSED_TIME)
    if current_time - start_time > 60000:
        spawning_allowed = False
    
    patient_near_entry = any(s['x'] > -1.05 and s['x'] < -0.8 for s in patients)
    patient_near_exit = any(s['x'] > 1.8 and s['x'] < 2.0 for s in patients)
    patient_near_pharmacy = any(s['x'] > 1.25 and s['x'] < 1.45 for s in patients)
    
    entry_door_angle = min(90, entry_door_angle + 5) if patient_near_entry else max(0, entry_door_angle - 5)
    exit_door_angle = min(90, exit_door_angle + 5) if patient_near_exit else max(0, exit_door_angle - 5)
    pharmacy_door_angle = min(90, pharmacy_door_angle + 5) if patient_near_pharmacy else max(0, pharmacy_door_angle - 5)
    
    to_remove = []
    
    for i, s in enumerate(patients):
        s['is_walking'] = False
        
        if s['state'] == 'walking_to_reception':
            s['x'] += PATIENT_SPEED * speed_multiplier
            s['is_walking'] = True
            if s['x'] >= -0.35:
                if s['id'] not in queue:
                    queue.append(s['id'])
                    s['state'] = 'in_queue'
                    speak(f"Hello, I'm {s['name']}. I need medical help.", 
                          f"ሰላም፣ እኔ {s['name']} ነኝ። ህክምና እፈልጋለሁ።")
                    
        elif s['state'] == 'in_queue':
            if random.random() < 0.005:
                speak(f"How long do I have to wait, {s['name']}?", 
                      f"ምን ያህል ጊዜ መጠበቅ አለብኝ {s['name']}?")
                
        elif s['state'] == 'moving_to_receptionist':
            s['is_walking'] = True
            if abs(s['x'] - (receptionist['x'] - 0.08)) < HITBOX_SENSITIVITY:
                s['has_prescription'] = True
                s['state'] = 'walking_to_consultation'
                if queue:
                    queue.pop(0)
                doctor_occupied = False
                speak(f"Thank you, I'll see the doctor now, {s['name']}.", 
                      f"አመሰግናለሁ፣ አሁን ዶክተሩን አገኛለሁ {s['name']}።")
            else:
                s['x'] += PATIENT_SPEED * speed_multiplier
                
        elif s['state'] == 'walking_to_consultation':
            s['x'] += PATIENT_SPEED * speed_multiplier
            s['is_walking'] = True
            if s['x'] >= 0.05:
                s['state'] = 'finding_room'
                
        elif s['state'] == 'finding_room':
            for idx, r in enumerate(consultation_rooms):
                if r['status'] == 'clean':
                    s['room_idx'] = idx
                    r['status'] = 'occupied'
                    s['state'] = 'moving_to_room'
                    break
                    
        elif s['state'] == 'moving_to_room':
            s['is_walking'] = True
            target = consultation_rooms[s['room_idx']]['x'] - 0.04
            if abs(s['x'] - target) < HITBOX_SENSITIVITY:
                s['state'] = 'waiting_for_doctor'
                s['wait_timer'] = WAITING_ROOM_DURATION
                s['is_sitting'] = True
            else:
                s['x'] += PATIENT_SPEED * speed_multiplier
                
        elif s['state'] == 'waiting_for_doctor':
            s['wait_timer'] -= speed_multiplier
            if s['wait_timer'] <= 0:
                s['state'] = 'in_consultation'
                s['consultation_timer'] = CONSULTATION_DURATION
                consultation_active = True
                current_patient_idx = i
                doctor['examining'] = True
                speak(f"Hello {s['name']}, I'm Dr. Smith. What brings you here today?",
                      f"ሰላም {s['name']}፣ እኔ ዶክተር ስሚዝ ነኝ። ዛሬ ምን ጉዳይ አምጥቶሃል?", is_doctor=True)
                
        elif s['state'] == 'in_consultation':
            s['consultation_timer'] -= speed_multiplier
            
            if s['consultation_timer'] <= 0:
                prescriptions = {
                    'head': 'Paracetamol',
                    'arm': 'Ibuprofen',
                    'leg': 'Ibuprofen',
                    'fever': 'Aspirin',
                    'cough': 'Amoxicillin',
                    'chest': 'Vitamin C',
                    'stomach': 'Omeprazole',
                    'psychology': 'Vitamin C'
                }
                prescribed = prescriptions.get(s['injury_type'], 'Vitamin C')
                s['prescribed_med'] = prescribed
                update_medicine_stock(prescribed, 10)
                speak(f"I'm prescribing {prescribed} for you, {s['name']}. Please pick it up at the pharmacy.",
                      f"{prescribed} ላዝ እዘዝልሃለሁ {s['name']}። እባክህ ከፋርማሲ ተቀበለው።", is_doctor=True)
                s['state'] = 'waiting_for_treatment'
                s['treatment_timer'] = TREATMENT_DURATION
                consultation_active = False
                doctor['examining'] = False
                current_patient_idx = -1
                last_voice_stage = None
                
        elif s['state'] == 'waiting_for_treatment':
            s['treatment_timer'] -= speed_multiplier
            if random.random() < 0.004:
                speak(f"I'm feeling better already, {s['name']}.", 
                      f"ቀድሞውንም እየተሻለኝ ነው {s['name']}።")
            if s['treatment_timer'] <= 0:
                s['state'] = 'walking_to_pharmacy'
                s['is_sitting'] = False
                
        elif s['state'] == 'walking_to_pharmacy':
            s['is_walking'] = True
            target = 1.38
            if s['x'] < target:
                s['x'] += PATIENT_SPEED * speed_multiplier
            else:
                s['state'] = 'in_pharmacy'
                s['pharmacy_timer'] = PHARMACY_VISIT_DURATION
                s['is_sitting'] = False
                speak(f"I need to pick up my {s['prescribed_med']} prescription, {s['name']}.",
                      f"{s['prescribed_med']} ማዘዣዬን መውሰድ እፈልጋለሁ {s['name']}።")
                
        elif s['state'] == 'in_pharmacy':
            s['pharmacy_timer'] -= speed_multiplier
            if s['pharmacy_timer'] <= 0:
                s['has_medicine'] = True
                s['state'] = 'leaving_pharmacy'
                speak(f"Thank you, I got my medicine, {s['name']}.", 
                      f"አመሰግናለሁ፣ መድሀኒቴን አገኘሁ {s['name']}።")
                
        elif s['state'] == 'leaving_pharmacy':
            s['is_walking'] = True
            if s['x'] > 0.75:
                s['x'] -= PATIENT_SPEED * speed_multiplier
            else:
                if s['room_idx'] != -1:
                    consultation_rooms[s['room_idx']]['status'] = 'dirty'
                s['state'] = 'walking_to_exit'
                s['is_sitting'] = False
                speak(f"Thanks for everything, goodbye {s['name']}.", 
                      f"ለሁሉም ነገር አመሰግናለሁ፣ ደህና ሁን {s['name']}።")
                
        elif s['state'] == 'walking_to_exit':
            s['is_walking'] = True
            s['x'] += PATIENT_SPEED * speed_multiplier
            if s['x'] > 2.1:
                if spawning_allowed:
                    s['x'] = -1.8
                    s['state'] = 'walking_to_reception'
                    s['room_idx'] = -1
                    s['injury_type'] = random.choice(['arm', 'head', 'leg', 'fever', 'cough', 'chest', 'stomach', 'psychology'])
                    s['pain_level'] = random.randint(1, 10)
                    s['has_medicine'] = False
                    s['has_prescription'] = False
                    s['is_sitting'] = False
                    s['prescribed_med'] = None
                    s['consultation_progress'] = 0
                else:
                    to_remove.append(s)
    
    for s in to_remove:
        if s in patients:
            patients.remove(s)
    
    for r in consultation_rooms:
        if r['status'] == 'dirty':
            r['clean_timer'] += speed_multiplier
            if r['clean_timer'] > CLEANING_DELAY:
                r['status'] = 'clean'
                r['clean_timer'] = 0
    
    if not doctor_occupied and queue and not consultation_active:
        doctor_occupied = True
        for s in patients:
            if s['id'] == queue[0]:
                s['state'] = 'moving_to_receptionist'
    
    glutPostRedisplay()
    glutTimerFunc(16, update, 0)

def keyboard(key, x, y):
    global game_active, entry_door_angle, exit_door_angle, pharmacy_door_angle
    global walk_anim, paused, speed_multiplier, help_text, help_timer, spawning_allowed
    global CONSULTATION_DURATION, PATIENT_SPEED, next_mode
    
    if key == b'r' or key == b'R':
        reset_simulation()
        entry_door_angle = 0.0
        exit_door_angle = 0.0
        pharmacy_door_angle = 0.0
        walk_anim = 0.0
        help_text = "Simulation Reset"
        help_timer = 60
        speak("Simulation has been reset", is_doctor=False)
        glutPostRedisplay()
    elif key == b'o' or key == b'O':
        entry_door_angle = 90.0
        exit_door_angle = 90.0
        pharmacy_door_angle = 90.0
        help_text = "Doors Opened"
        help_timer = 60
        speak("All doors opened", is_doctor=False)
        glutPostRedisplay()
    elif key == b'p' or key == b'P':
        paused = not paused
        help_text = "Paused" if paused else "Resumed"
        help_timer = 60
        speak("Simulation paused" if paused else "Simulation resumed", is_doctor=False)
    elif key == b's' or key == b'S':
        if spawning_allowed:
            spawn_patient(len(patients))
            help_text = "Patient spawned"
            help_timer = 60
            speak("New patient has arrived", is_doctor=False)
    elif key == b'f' or key == b'F':
        speed_multiplier = min(5.0, speed_multiplier + 0.5)
        help_text = f"Speed: {speed_multiplier}x"
        help_timer = 60
        speak(f"Speed increased to {speed_multiplier} times", is_doctor=False)
    elif key == b'n' or key == b'N':
        next_mode = not next_mode
        help_text = "Next Mode: " + ("ON - Press SPACE to advance" if next_mode else "OFF")
        help_timer = 60
        speak("Next mode enabled" if next_mode else "Next mode disabled", is_doctor=False)
    elif key == b' ':
        if next_mode:
            advance_next_patient()
            help_text = "Patient advanced to next state"
            help_timer = 30
            speak("Patient advanced to next stage", is_doctor=False)
    elif key == b'h' or key == b'H':
        help_text = "R:Reset O:Open P:Pause S:Spawn F:Fast N:NextMode SPACE:Advance 1-6:Adjust Q:Quit"
        help_timer = 180
        speak("Help menu displayed", is_doctor=False)
    elif key == b'1':
        CONSULTATION_DURATION = min(2400, CONSULTATION_DURATION + 100)
        help_text = f"Consultation: {CONSULTATION_DURATION}"
        help_timer = 60
        speak(f"Consultation duration increased to {CONSULTATION_DURATION}", is_doctor=False)
    elif key == b'2':
        CONSULTATION_DURATION = max(300, CONSULTATION_DURATION - 100)
        help_text = f"Consultation: {CONSULTATION_DURATION}"
        help_timer = 60
        speak(f"Consultation duration decreased to {CONSULTATION_DURATION}", is_doctor=False)
    elif key == b'3':
        PATIENT_SPEED = min(0.02, PATIENT_SPEED + 0.001)
        help_text = f"Speed: {PATIENT_SPEED:.3f}"
        help_timer = 60
        speak(f"Patient movement speed increased", is_doctor=False)
    elif key == b'4':
        PATIENT_SPEED = max(0.003, PATIENT_SPEED - 0.001)
        help_text = f"Speed: {PATIENT_SPEED:.3f}"
        help_timer = 60
        speak(f"Patient movement speed decreased", is_doctor=False)
    elif key == b'5':
        for med in medicine_inventory:
            medicine_inventory[med]['stock'] += 10
        help_text = "Added +10 to all medicines"
        help_timer = 60
        speak("Added 10 to all medicine stocks", is_doctor=False)
    elif key == b'6':
        for med in medicine_inventory:
            medicine_inventory[med]['stock'] = max(0, medicine_inventory[med]['stock'] - 5)
        help_text = "Removed -5 from all medicines"
        help_timer = 60
        speak("Removed 5 from all medicine stocks", is_doctor=False)
    elif key == b'q' or key == b'Q' or key == b'\x1b':
        global speech_thread_running
        speech_thread_running = False
        speech_queue.put(None)
        speak("Shutting down clinic simulation", is_doctor=False)
        time.sleep(0.5)
        glutLeaveMainLoop()
        sys.exit(0)

def reshape(width, height):
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    aspect = width / height
    if width >= height:
        glOrtho(-1.8 * aspect, 2.8 * aspect, -0.9, 0.9, -1, 1)
    else:
        glOrtho(-1.8, 2.8, -0.9 / aspect, 0.9 / aspect, -1, 1)
    glMatrixMode(GL_MODELVIEW)

def cleanup():
    global speech_thread_running
    speech_thread_running = False
    print("Shutting down clinic simulation...")

def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1600, 800)
    glutInitWindowPosition(50, 50)
    glutCreateWindow("Medical Clinic - Full Voice Dialog with Controls".encode("utf-8"))
    
    glShadeModel(GL_SMOOTH)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glClearColor(0.55, 0.75, 0.95, 1.0)
    glEnable(GL_LINE_SMOOTH)
    glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
    
    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(keyboard)
    
    reset_simulation()
    init_tts()
    load_background_texture(background_image_path)
    glutTimerFunc(0, update, 0)
    
    print("=" * 70)
    print("🏥 MEDICAL CLINIC SIMULATION - FULL VOICE DIALOG")
    print("=" * 70)
    print("👥 PATIENT NAMES (in order):")
    print("   1. Kindu (Headache)")
    print("   2. Mastewal (Psychology - Anger)")
    print("   3. Belaynesh (Stomach)")
    print("   4. Siteru (Random)")
    print("   5. Megbat (Random)")
    print("   6. Alebachew (Random)")
    print("")
    print("📍 DOCTOR POSITION: MOVED TO LEFT SIDE (x = -0.05)")
    print("")
    print("🗣️ FULL VOICE DIALOG FEATURES:")
    print("  ✓ Doctor asks detailed medical questions")
    print("  ✓ Patient provides complete symptom descriptions")
    print("  ✓ Bilingual support (English + Amharic)")
    print("  ✓ Sequential voice playback (no overlap)")
    print("  ✓ Natural conversation pacing (2.5 sec between responses)")
    print("  ✓ Voice feedback for all control actions")
    print("")
    print("🎮 CONTROLS (Also shown on screen):")
    print("  R - Reset simulation")
    print("  O - Open all doors")
    print("  P - Pause/Resume")
    print("  S - Spawn new patient")
    print("  F - Increase speed")
    print("  N - Toggle Next Mode (Manual Advancement)")
    print("  SPACE - Advance patient (when Next Mode ON)")
    print("  1 - Longer consultation")
    print("  2 - Shorter consultation")
    print("  3 - Faster patient movement")
    print("  4 - Slower patient movement")
    print("  5 - Add medicine stock")
    print("  6 - Remove medicine stock")
    print("  H - Show help")
    print("  Q or ESC - Quit")
    print("=" * 70)
    print("💡 TIP: Press N to enable Next Mode, then press SPACE to advance patients manually!")
    print("💡 Voice feedback is enabled for all control actions!")
    print("=" * 70)
    
    # Welcome voice message
    speak("Welcome to the Medical Clinic Simulation. Press H for help.", is_doctor=False)
    
    try:
        glutMainLoop()
    except KeyboardInterrupt:
        print("\nSimulation ended")
        cleanup()
        sys.exit(0)

if __name__ == "__main__":
    main()