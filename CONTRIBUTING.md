# Contributing to SentryCage

Thanks for considering contributing — SentryCage is 100% open source now, and it gets better with every pair of eyes on it. This doc is meant to make it easy to get started, not to gatekeep. If something here is unclear, that's a bug in this doc — open an issue about it.

---

## Ways to contribute

You don't have to write code to help:

- **Report bugs** — [open an issue](https://github.com/SentryCage/sentrycage/issues) with steps to reproduce, your OS/Python version, and relevant logs
- **Suggest a signal or chain** — open an issue describing the idea, even without code
- **Improve docs** — typos, unclear setup steps, missing troubleshooting cases
- **Answer questions** — help other users in Issues/Discussions
- **Write code** — bug fixes, new signals, new chains, new LLM providers, tests

---

## Development setup

```bash
git clone https://github.com/SentryCage/sentrycage.git
cd sentrycage

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# fill in ETHERSCAN_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
# (use a throwaway/test bot for development)

pytest -v
```

All 75 tests should pass before you start. If they don't, check [README → Troubleshooting](README.md#troubleshooting) first — it's likely environment, not code.

---

## Before you open a Pull Request

1. **Open an issue first for anything non-trivial** (new signal type, new chain, architectural change). Saves everyone time if the idea needs discussion before code.
2. **Keep PRs focused.** One fix or one feature per PR — easier to review, easier to merge.
3. **Add/update tests.** New logic needs tests. Bug fixes should include a regression test where practical.
4. **Run the full suite before pushing:**
   ```bash
   pytest --cov=src --cov-report=term-missing
   ```
5. **Follow existing code style.** Look at neighboring files for conventions (naming, docstrings, structure) rather than introducing a new style.
6. **Update docs if behavior changes** — README, `.env.example`, or relevant docstrings.

---

## Adding a new chain

Chains are configured in `src/config/` (see `Chain` enum and related wallet/chain config). A new chain typically needs:

- Chain ID + Etherscan V2 endpoint mapping
- Test coverage confirming fetch + signal generation work against that chain
- A one-line mention in the README's chain list if it's a notable addition

## Adding a new signal type

Look at how existing signals (accumulation, distribution, CEX deposit/withdrawal, large transfer, unusual activity) are implemented and tested — new signals should follow the same shape: detection logic, a clear "what does this mean" reasoning hook, and dedicated tests.

## Adding an LLM provider

`LLM_PROVIDER` currently supports `ollama`, `claude`, `openai`, `lmstudio`. If you want to add another provider, keep the same interface contract so the reasoning fallback logic (AI → rule-based) keeps working without special-casing.

---

## Code of conduct

Be respectful, be patient with newcomers, assume good faith. Disagreements about code/design are normal and welcome — keep them about the code, not the person.

---

## Licensing note

By contributing, you agree your contribution is licensed under the same terms as the project — **MIT** (see [LICENSE](LICENSE)). In short: your code stays free and open for everyone, forever.

---

## Questions?

Open a [GitHub Discussion](https://github.com/SentryCage/sentrycage/discussions) or an issue. We'd rather answer a "dumb" question early than review a PR built on a misunderstanding.
