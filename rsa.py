import base64
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as Cipher_pkcs1_v1_5


def rsa_encrypt(message, pub_key: str) -> str:
    rsakey = RSA.importKey(
        "-----BEGIN RSA PUBLIC KEY-----\n" + pub_key + "\n-----END RSA PUBLIC KEY-----"
    )
    cipher = Cipher_pkcs1_v1_5.new(rsakey)
    cipher_text = base64.b64encode(cipher.encrypt(message.encode("utf-8")))
    return cipher_text.decode("utf-8")
