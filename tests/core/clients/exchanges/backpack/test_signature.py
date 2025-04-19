from src.core.clients.exchanges.backpack.backpack import BackpackExchangeClient


def test_signature():
    client = BackpackExchangeClient(
        base_url="https://api.backpack.exchange",
        api_key="aapsz3keT9b74txaecFeMInpc4gs5bm2XfRgMjMgOlf=",
        api_secret="hq16awOPV0b7gIzwfKgoSreihtjaaBqbbhrsbl966Fs=",
    )

    signature = client._generate_signature(action="buy", timestamp=12345)

    assert (
        signature
        == "fAcpXXOmq8i4SbBFgeqIUgKxYSHXTsJmBX96HsWfs9uFsLKTXzk7x5iZGVq06v8n2Ptk3zU1BxnYy/RHsaEYDg=="
    )


def test_signature_with_optional_fields():
    # TODO
    pass
