import random


def verify_english_word(word: str) -> bool:
    with open("data/words.txt") as f:
        text_file = f.read().splitlines()

    for i in text_file:
        if i == word:
            return True

    return False


def get_random_english_word() -> str:
    with open("data/words.txt") as f:
        text_file = f.read().splitlines()

    return random.choice(text_file)

def scramble_word(word):
    # If word is too short to scwambwe, wetuwn it as it is >w<
    if len(word) <= 3:
        return word

    # Keep the fiwst and wast wetters in pwace
    middle = list(word[1:-1])
    random.shuffle(middle)
    return word[0] + ''.join(middle) + word[-1]
