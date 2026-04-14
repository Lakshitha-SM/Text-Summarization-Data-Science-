from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_NAME = "sshleifer/distilbart-cnn-6-6"

def download():
    print(f"Downloading model {MODEL_NAME}...")
    try:
        AutoTokenizer.from_pretrained(MODEL_NAME)
        AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
        print("Success: Model downloaded and cached.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    download()
