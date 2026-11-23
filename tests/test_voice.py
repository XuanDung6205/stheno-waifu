
from src.voice.clit import SthenoVoice

voice = SthenoVoice()

voice.initialize()

voice.speak(
    "Anh đây. Hôm nay em sẽ nói chuyện với anh bằng giọng của em nhé!",
    wait=False
)

print("Is speaking:", voice.is_speaking)

# Muốn ngắt:
# voice.stop()

# Muốn chờ nói hết:
# voice.speak("Em đang thử kiểm tra giọng nói.", wait=True)

# Khi kết thúc:
# voice.shutdown()
