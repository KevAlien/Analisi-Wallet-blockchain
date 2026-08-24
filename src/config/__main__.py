"""
CLI di stato: python -m src.config status

SentryCage è open source e gratuito — non esistono più comandi
activate/deactivate legati a una license key o a un server esterno.
"""
import sys


def cmd_status() -> None:
    from src.database.sqlite import init_db
    from src.config.license import get_active_features

    init_db()
    features = get_active_features()

    print(f"\nTier attivo    : {features.display_tier}")
    print(f"AI reasoning   : {'✓' if features.ai_reasoning else '✗'}")
    print(f"Chains         : {', '.join(sorted(features.chains))}")
    print("\nSentryCage è open source: tutte le feature sono gratuite per tutti.")
    print()


COMMANDS = {
    "status": cmd_status,
}

if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] not in COMMANDS:
        print(f"Uso: python -m src.config <{'|'.join(COMMANDS)}>")
        sys.exit(1)

    COMMANDS[argv[0]]()
