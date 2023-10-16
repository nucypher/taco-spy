import os

from hexbytes import HexBytes
from nucypher.blockchain.eth.signers import InMemorySigner
from nucypher.characters.lawful import Bob, Enrico
from nucypher.policy.conditions.lingo import ConditionLingo
from nucypher_core import ThresholdMessageKit
from nucypher_core.ferveo import DkgPublicKey

from nucypher.utilities.logging import GlobalLoggerSettings

GlobalLoggerSettings.start_console_logging()


def _get_conditions():
    eth_balance_condition = {
        "version": ConditionLingo.VERSION,
        "condition": {
            "conditionType": "rpc",
            "chain": 80001,
            "method": "eth_getBalance",
            "parameters": ["0x210eeAC07542F815ebB6FD6689637D8cA2689392", "latest"],
            "returnValueTest": {"comparator": "==", "value": 0},
        },
    }
    return eth_balance_condition


def encrypt(
        message: bytes,
        dk_public_key: bytes,
        enrico_secret: bytes
) -> ThresholdMessageKit:
    dkg_public_key = DkgPublicKey.from_bytes(dk_public_key)
    signer = InMemorySigner(private_key=enrico_secret)
    enrico = Enrico(encrypting_key=dkg_public_key, signer=signer)
    eth_balance_condition = _get_conditions()
    threshold_message_kit = enrico.encrypt_for_dkg(
        plaintext=message,
        conditions=eth_balance_condition
    )
    return threshold_message_kit


def decrypt(
        domain: str,
        eth_endpoint: str,
        polygon_endpoint: str,
        threshold_message_kit: ThresholdMessageKit
) -> bytes:
    bob = Bob(
        domain=domain,
        eth_endpoint=eth_endpoint,
        polygon_endpoint=polygon_endpoint,
    )
    cleartext = bob.threshold_decrypt(
        threshold_message_kit=threshold_message_kit,
    )
    cleartext = bytes(cleartext)
    return cleartext


def simple_taco():
    eth_endpoint = os.environ["DEMO_L1_PROVIDER_URI"]
    polygon_endpoint = os.environ["DEMO_L2_PROVIDER_URI"]
    domain = os.environ["DEMO_DOMAIN"]
    enrico_secret = HexBytes(os.environ["DEMO_ENRICO_PRIVATE_KEY"])
    dkg_public_key = HexBytes(os.environ["DEMO_DKG_PUBLIC_KEY"])

    try:

        # encrypt
        print(f"DKG Public Key: {dkg_public_key.hex()}")
        message = "hello world".encode()
        threshold_message_kit = encrypt(message, dkg_public_key, enrico_secret)

        # decrypt
        cleartext = decrypt(domain, eth_endpoint, polygon_endpoint, threshold_message_kit)
        print(f"Decrypted message: {cleartext}")
        return cleartext == message

    except Exception as e:
        print(f"Failed to decrypt: {e}")
        return False
