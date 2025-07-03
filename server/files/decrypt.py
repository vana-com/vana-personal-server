import pgpy


def decrypt(encryption_key: str, content: str) -> str:
    message = pgpy.PGPMessage.from_blob(content)
    decrypted_message = message.decrypt(encryption_key)
    return str(decrypted_message.message)
