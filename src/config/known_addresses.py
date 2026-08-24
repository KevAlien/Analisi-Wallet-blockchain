"""
Indirizzi noti di exchange e protocolli DeFi — fonte di verità unica.
Importare da qui invece di ridefinire in ogni modulo.
"""

# Indirizzi CEX (Centralized Exchange) — (nome, tipo)
CEX_ADDRESSES: dict[str, tuple[str, str]] = {
    "0x28c6c06298d514db089934071355e5743bf21d60": ("Binance", "deposit"),
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549": ("Binance", "withdrawal"),
    "0xdfd5293d8e347dfe59e90efd55b2956a1343963d": ("Coinbase", "deposit"),
    "0x3cd751e6b0078be393132286c442345e5dc49699": ("Coinbase", "hot wallet"),
}

# Lista flat degli indirizzi CEX (per membership check rapido)
CEX_ADDRESS_LIST: list[str] = list(CEX_ADDRESSES.keys())


def get_exchange_name(address: str) -> str:
    """Restituisce il nome dell'exchange per un dato indirizzo (case-insensitive)."""
    entry = CEX_ADDRESSES.get(address.lower())
    return entry[0] if entry else "Unknown Exchange"
