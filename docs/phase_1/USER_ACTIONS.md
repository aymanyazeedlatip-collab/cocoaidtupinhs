# User Actions After Phase 1

No manual code editing is required.

After downloading and extracting the Phase 1 package on Windows:

1. Keep the Phase 0 ZIP as a backup.
2. Extract the Phase 1 ZIP into a new folder. Do not overwrite the Phase 0 folder.
3. Double-click `setup.bat` while connected to the internet.
4. Wait for `COCO-AID verification passed` and `SETUP COMPLETE`.
5. Double-click `test.bat` and confirm all tests pass.
6. Run `run.bat`.
7. Open `http://127.0.0.1:8000/api/v2/health` and confirm:
   - `status` is `healthy`;
   - `contract_api_version` is `3.0.0-draft.1`;
   - `model_runtime.compatible` is `true`;
   - migration 1 is `applied`.

If `model_runtime.compatible` is false, activate the project environment and run:

```powershell
.\.venv\Scripts\activate
python -m pip install --upgrade --force-reinstall scikit-learn==1.9.0
python scripts\verify_installation.py
python -m pytest -q
```

Do not run `python scripts\migrations.py downgrade-one --allow-destructive` on a real project database. That command exists only for migration testing and would delete the legacy tables.
