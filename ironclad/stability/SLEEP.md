# RG353V sleep brightness guard (development)

The original RK3566 systemd sleep hook writes current brightness to /var/local/cur_bright.state and restores it without validating its contents. If the saved value is absent, zero, or corrupt, the panel may remain dark after waking.

This branch adds a Python guard for the **RG353V image only**, installed by ironclad/integrate-image.sh. The original upstream RK3566 script is not changed in source; only the staged RG353V image copy is patched.

- Saves a positive brightness value to /run/ironclad/brightness-before-suspend before dimming the backlight.
- Restores the saved valid value when the system wakes.
- If the saved value is invalid or missing and brightness is zero, uses 25% of maximum as a visible fallback.
- Leaves an already-lit display alone when the saved value is missing.
- Refuses to dim if the current brightness or maximum cannot be read or state cannot be saved.
- Stops installation if the upstream hook's expected brightness lines have changed.
- Leaves all other existing upstream sleep/wake operations in place.
- Does not access TF2, ROMs, saves, or emulators.

**Limitations:** This handles brightness state only. It cannot recover a hung GPU, firmware suspend failure, broken backlight driver, or general sleep failure. Hardware behavior is untested; test on a spare TF1 card, including brightness at different levels, repeated suspend/resume, and low battery.

Run tests: `python3 -m unittest discover -v -s ironclad/stability -p 'test_*.py'`.
