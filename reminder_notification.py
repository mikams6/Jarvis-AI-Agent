import os
import subprocess
import sys
import ctypes
from pathlib import Path

from winotify import Notification, audio


TOAST_APP_ID = "Jarvis"


def set_jarvis_app_user_model_id() -> None:
    if os.name != "nt":
        return

    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    set_app_user_model_id = shell32.SetCurrentProcessExplicitAppUserModelID
    set_app_user_model_id.argtypes = [ctypes.c_wchar_p]
    set_app_user_model_id.restype = ctypes.c_long
    result = set_app_user_model_id(TOAST_APP_ID)
    if result != 0:
        raise OSError(
            f"Could not set the Jarvis Windows app identity "
            f"(HRESULT 0x{result & 0xFFFFFFFF:08X})."
        )


def ensure_jarvis_icon(icon_directory: Path | None = None) -> tuple[Path, Path]:
    from PIL import Image, ImageOps

    if icon_directory is None:
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            raise RuntimeError("Could not locate the current user's local app data folder.")
        icon_directory = Path(local_app_data) / "Jarvis" / "assets"

    logo_path = Path(__file__).resolve().with_name("jarvis_logo.jpg")
    if not logo_path.is_file():
        raise FileNotFoundError(f"Could not find the Jarvis logo image: {logo_path}")

    icon_directory.mkdir(parents=True, exist_ok=True)
    png_path = icon_directory / "jarvis-icon.png"
    ico_path = icon_directory / "jarvis-icon.ico"
    with Image.open(logo_path) as source_image:
        image = ImageOps.exif_transpose(source_image).convert("RGB")
        image = ImageOps.fit(
            image,
            (256, 256),
            method=Image.Resampling.LANCZOS,
        )
        image.save(png_path, format="PNG")
        image.save(
            ico_path,
            format="ICO",
            sizes=[
                (16, 16),
                (24, 24),
                (32, 32),
                (48, 48),
                (64, 64),
                (128, 128),
                (256, 256),
            ],
        )
    return png_path, ico_path


def register_toast_app(shortcut_directory: Path | None = None) -> None:
    if os.name != "nt":
        raise RuntimeError("Windows toast registration is only supported on Windows.")

    from win32com.client import Dispatch
    from win32com.propsys import propsys, pscon  # type: ignore[reportMissingModuleSource]
    from win32com.shell import shellcon  # type: ignore[reportMissingModuleSource]

    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.is_file():
        raise RuntimeError(f"Could not find the GUI Python executable: {pythonw}")
    _, ico_path = ensure_jarvis_icon()

    shell = Dispatch("WScript.Shell")
    app_script = Path(__file__).resolve().with_name("agent.py")
    if shortcut_directory is None:
        app_data = os.environ.get("APPDATA")
        if not app_data:
            raise RuntimeError("Could not locate the current user's Windows Start menu.")
        shortcut_directory = (
            Path(app_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        )
    desktop_directory = Path(shell.SpecialFolders("Desktop"))
    shortcut_directories = {shortcut_directory, desktop_directory}
    for directory in shortcut_directories:
        directory.mkdir(parents=True, exist_ok=True)
        shortcut_path = directory / "Jarvis.lnk"

        shortcut = shell.CreateShortcut(str(shortcut_path))
        shortcut.TargetPath = str(pythonw)
        shortcut.Arguments = subprocess.list2cmdline([str(app_script)])
        shortcut.WorkingDirectory = str(app_script.parent)
        shortcut.Description = "Jarvis local assistant"
        shortcut.IconLocation = f"{ico_path},0"
        shortcut.Save()
        del shortcut

        property_store = propsys.SHGetPropertyStoreFromParsingName(
            str(shortcut_path),
            None,
            shellcon.GPS_READWRITE,
        )
        property_store.SetValue(
            pscon.PKEY_AppUserModel_ID,
            propsys.PROPVARIANTType(TOAST_APP_ID),
        )
        property_store.Commit()
        del property_store


def show_toast(
    title: str,
    message: str,
    reminder_audio_path: Path | None = None,
) -> None:
    register_toast_app()
    png_path, _ = ensure_jarvis_icon()
    message = message.replace("`", "``").replace("$", "`$")
    message = message.replace("]]>", "]]]]><![CDATA[>")
    notification = Notification(
        app_id=TOAST_APP_ID,
        title=title,
        msg=message,
        icon=str(png_path),
        duration="long",
    )
    notification.set_audio(audio.Default, loop=False)
    notification.show()
    if title == "Reminder":
        if reminder_audio_path is not None and reminder_audio_path.is_file():
            from agent import play_reminder_audio

            try:
                play_reminder_audio(reminder_audio_path)
            finally:
                reminder_audio_path.unlink(missing_ok=True)
        else:
            from agent import speak_reminder

            speak_reminder(f"Reminder. {message}")


def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] == "--test":
        show_toast(
            "Jarvis notifications",
            "Test notification. Enable Jarvis in Windows Settings > System > Notifications.",
        )
        return
    if (
        len(sys.argv) == 4
        and sys.argv[1] == "--scheduled"
        and sys.argv[2].strip()
        and sys.argv[3].strip()
    ):
        show_toast(
            "Reminder",
            " ".join(sys.argv[2].split()),
            Path(sys.argv[3]),
        )
        return
    if len(sys.argv) != 2 or not sys.argv[1].strip():
        raise SystemExit("Expected reminder text, --test, or --scheduled details.")

    show_toast("Reminder", " ".join(sys.argv[1].split()))


if __name__ == "__main__":
    main()
