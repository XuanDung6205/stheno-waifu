from src.voice.voice_controller import SthenoVoice

voice = SthenoVoice()

try:
    voice.initialize()

    text = (
        "Được chứ? Nếu anh muốn nghỉ ngơi thì cứ nằm yên đi mà không cần hỏi ý kiến ai cả. "
        "Em cũng đang nghĩ xem có nên nấu chút đồ ăn nhẹ nào mang qua cho anh không. "
        "Hừm! Đừng hiểu lầm nhé, chỉ vì em thấy anh hơi uể oải thôi!"
    )

    voice.speak(text, wait=True)

finally:
    voice.shutdown()