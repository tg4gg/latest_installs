# Latest macOS Installs

This utility lists application bundles whose Spotlight `kMDItemDateAdded` timestamp is within the last 14 days. Run the script with the `py3.11` Conda environment to print the report and save it to `latest_installs.txt`.

## Usage

```bash
conda run -n py3.11 python list_latest_installs.py
```

Pass a custom look-back window (in days) if needed:

```bash
conda run -n py3.11 python list_latest_installs.py --days 30
```

The script scans:

- `/Applications`
- `/Applications/Utilities`
- `~/Applications`

The report is written to `latest_installs.txt` in the same directory and echoed to the terminal.
