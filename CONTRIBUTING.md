# Contributing

Bug reports and focused pull requests are welcome.

Before submitting a change:

1. Do not add game ISOs, extracted assets, translation data, savestates,
   memory dumps, third-party binaries, or generated build output.
2. Run `python -m unittest discover -s tests -p "test_*.py"` from the project
   virtual environment.
3. Keep executable signatures and safety checks fail-closed. An unknown game
   revision or dialogue structure must disable/fallback rather than patch an
   unverified address.
4. Document new runtime addresses with the game revision, evidence, and a
   reproducible capture method.

Reports should include the PPSSPP version, ISO edition/hash where legally
shareable, plugin build hash, relevant log excerpt, reproduction steps, and a
screenshot. Never upload copyrighted game content.
