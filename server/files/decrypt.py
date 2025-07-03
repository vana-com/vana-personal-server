import pgpy


def decrypt(encryption_key: str, content: str) -> str:
    message = pgpy.PGPMessage.from_blob(content)
    return message.decrypt(encryption_key)
