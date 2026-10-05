import os

# пути 
VIDEO_FOLDER = r"C:\Users\Lorena.s\Desktop\aifordota"
VIDEO_PATH = r""    
AUDIO_PATH = r""  
DB_PATH = "highlights.db"

MATCH_ID = 8960882635

# горн
KNOWN_VIDEO_TIMESTAMP = "16:42"
KNOWN_GAME_TIMER = "00:00"

# каналы
USE_OCR = True
USE_YOLO = False
USE_WHISPER = False
USE_GAME = True
USE_GAME_SOURCE = "parser"     
PARSER_DIR = r"C:\Users\Lorena.s\Desktop\aifordota"

# проверка
VIDEO_STEP_SEC = 1.0
OCR_EVERY = 1
YOLO_EVERY = 3
AUDIO_CHUNK_SEC = 0.5

# границы
MOTION_Q = 0.92
VOLUME_Q = 0.98
RATE_Q = 0.97

# точки
MERGE_GAP = 7
MIN_DURATION = 15
OCR_BACKSHIFT = 5
PRE_PAD = 12
POST_PAD = 18
MAX_DURATION = 45
SCORE_THRESHOLD = 3  

KEYWORDS = [
    "rampage", "ultra kill", "triple kill", "double kill",
    "killing spree", "godlike", "unstoppable", "roshan", "aegis",
    "barracks", "victory", "победа", "first blood",
    "проливает первую кровь", "тройное убийство",
    "двойное убийство", "серия убийств",
]

EVENT_SCORES = {
    # 5
    "rampage": 5, "godlike": 5, "aegis": 5, "match_end": 5,
    "victory": 5, "победа": 5,
    # 4
    "triple kill": 4, "тройное убийство": 4, "unstoppable": 4,
    "roshan": 4, "teamfight": 4, "barracks": 4, "gold_swing": 4,
    # 3
    "double kill": 3, "двойное убийство": 3, "killing spree": 3,
    "серия убийств": 3, "buyback": 3,
    # 2
    "first blood": 2, "проливает первую кровь": 2,
}

DEFAULT_OCR_SCORE = 2

CHANNEL_CONF = {
    "game": 0.85, "ocr": 0.70, "vision": 0.35,
    "motion": 0.35, "audio": 0.30,
}