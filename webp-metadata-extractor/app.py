#!/usr/bin/env python3
"""Media metadata extractor GUI using ExifTool."""

from __future__ import annotations

import json
import subprocess
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

APP_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = APP_DIR / "settings.json"
DEFAULT_EXIFTOOL_DIR = Path(r"C:\Users\Kittzy\Khan_Industries\Github\ExifTool")

FILE_EXTENSIONS = {
    "PNG (.png)": ".png",
    "WebP (.webp)": ".webp",
    "MP3 (.mp3)": ".mp3",
    "MP4 (.mp4)": ".mp4",
}

COMFYUI_WORKFLOW_EXPORT = "ComfyUI Workflow (.json)"

EXPORT_FORMATS = {
    "Markdown (.md)": ".md",
    "Plain Text (.txt)": ".txt",
    "JSON (.json)": ".json",
    "HTML (.html)": ".html",
    COMFYUI_WORKFLOW_EXPORT: ".json",
}

WORKFLOW_TAG_NAMES = {"workflow", "imagedescription"}
PROMPT_TAG_NAMES = {"prompt", "make"}
WORKFLOW_PREFIX = "workflow:"
PROMPT_PREFIX = "prompt:"

EXIFTOOL_EXE_NAMES = ("exiftool.exe", "exiftool(-k).exe", "exiftool")


@dataclass
class JobPlan:
    source_label: str
    input_files: list[Path]
    output_dir: Path
    export_ext: str
    export_label: str
    file_ext: str

    def output_path_for(self, input_file: Path) -> Path:
        if self.export_label == COMFYUI_WORKFLOW_EXPORT:
            return self.output_dir / f"{input_file.stem}_workflow.json"
        return self.output_dir / f"{input_file.stem}_metadata{self.export_ext}"


def load_settings() -> dict:
    if not SETTINGS_FILE.exists():
        return {"exiftool_dir": str(DEFAULT_EXIFTOOL_DIR)}
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"exiftool_dir": str(DEFAULT_EXIFTOOL_DIR)}
    if "exiftool_dir" not in data:
        data["exiftool_dir"] = str(DEFAULT_EXIFTOOL_DIR)
    return data


def save_settings(data: dict) -> None:
    SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def find_exiftool_in_dir(exiftool_dir: str) -> Path:
    if not exiftool_dir.strip():
        raise FileNotFoundError("Choose an ExifTool folder.")

    location = Path(exiftool_dir)
    if not location.exists():
        raise FileNotFoundError(f"ExifTool path does not exist:\n{location}")

    if location.is_file():
        return location

    for name in EXIFTOOL_EXE_NAMES:
        candidate = location / name
        if candidate.is_file():
            return candidate

    raise FileNotFoundError(
        f"No ExifTool executable found in:\n{location}\n\n"
        f"Expected one of: {', '.join(EXIFTOOL_EXE_NAMES)}"
    )


def collect_input_files(
    source_mode: str,
    source_path: Path,
    file_ext: str,
) -> list[Path]:
    if source_mode == "file":
        if source_path.suffix.lower() != file_ext:
            raise ValueError(f"Selected file must be a {file_ext} file.")
        return [source_path]

    if not source_path.is_dir():
        raise ValueError("Selected source folder does not exist.")

    files = sorted(
        path
        for path in source_path.iterdir()
        if path.is_file() and path.suffix.lower() == file_ext
    )
    if not files:
        raise ValueError(f"No {file_ext} files found in: {source_path}")
    return files


def build_job_plan(
    source_mode: str,
    source_path: str,
    output_dir: str,
    export_label: str,
    file_type_label: str,
) -> JobPlan:
    if not source_path.strip():
        raise ValueError("Choose an input file or folder.")
    if not output_dir.strip():
        raise ValueError("Choose an output folder.")

    source = Path(source_path)
    out = Path(output_dir)
    if not out.exists():
        raise ValueError("Output folder does not exist.")
    if not out.is_dir():
        raise ValueError("Output path must be a folder.")

    file_ext = FILE_EXTENSIONS[file_type_label]
    export_ext = EXPORT_FORMATS[export_label]
    files = collect_input_files(source_mode, source, file_ext)

    return JobPlan(
        source_label=str(source),
        input_files=files,
        output_dir=out,
        export_ext=export_ext,
        export_label=export_label,
        file_ext=file_ext,
    )


def run_exiftool(exiftool: Path, args: list[str]) -> str:
    result = subprocess.run(
        [str(exiftool), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "Unknown ExifTool error").strip()
        raise RuntimeError(detail)
    return result.stdout


def tag_base_name(tag: str) -> str:
    if ":" in tag:
        return tag.rsplit(":", 1)[-1]
    return tag


def read_metadata_dict(exiftool: Path, input_file: Path) -> dict:
    raw = run_exiftool(exiftool, ["-json", "-G", "-a", str(input_file)])
    payload = json.loads(raw)
    if not payload:
        return {}
    return payload[0]


def parse_embedded_json(value: object) -> object:
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str):
        raise ValueError("Embedded metadata is not valid JSON text.")
    text = value.strip()
    if not text:
        raise ValueError("Embedded metadata is empty.")
    return json.loads(text)


def is_comfyui_workflow_document(data: object) -> bool:
    return isinstance(data, dict) and isinstance(data.get("nodes"), list)


def strip_comfy_prefix(value: str, prefix: str) -> str | None:
    text = value.strip()
    if text.lower().startswith(prefix):
        return text[len(prefix) :].strip()
    return None


def find_prefixed_metadata(metadata: dict, prefix: str) -> str | None:
    for key, value in metadata.items():
        if key == "SourceFile" or value in (None, ""):
            continue
        stripped = strip_comfy_prefix(str(value), prefix)
        if stripped:
            return stripped
    return None


def find_metadata_value(metadata: dict, tag_names: set[str]) -> str | None:
    for key, value in metadata.items():
        if key == "SourceFile" or value in (None, ""):
            continue
        tag_name = tag_base_name(key).lower()
        text = str(value).strip()
        if tag_name in tag_names:
            for prefix in (WORKFLOW_PREFIX, PROMPT_PREFIX):
                stripped = strip_comfy_prefix(text, prefix)
                if stripped:
                    return stripped
            return text
    return None


def extract_comfyui_workflow(metadata: dict) -> dict:
    candidates: list[str] = []

    prefixed = find_prefixed_metadata(metadata, WORKFLOW_PREFIX)
    if prefixed:
        candidates.append(prefixed)

    workflow_raw = find_metadata_value(metadata, WORKFLOW_TAG_NAMES)
    if workflow_raw and workflow_raw not in candidates:
        candidates.append(workflow_raw)

    for raw in candidates:
        try:
            workflow = parse_embedded_json(raw)
        except ValueError:
            continue
        if is_comfyui_workflow_document(workflow):
            return workflow

    if candidates:
        raise ValueError("Found workflow metadata, but it is not a valid ComfyUI workflow JSON.")

    has_prompt = bool(find_prefixed_metadata(metadata, PROMPT_PREFIX)) or bool(
        find_metadata_value(metadata, PROMPT_TAG_NAMES)
    )
    if has_prompt:
        raise ValueError(
            "This image has a ComfyUI prompt, but no embedded workflow was found."
        )

    raise ValueError(
        "No ComfyUI workflow metadata found. "
        "Use images exported from ComfyUI with workflow embedding enabled."
    )


def preview_comfyui_workflow(metadata: dict) -> str:
    try:
        workflow = extract_comfyui_workflow(metadata)
    except ValueError as exc:
        return f"no workflow ({exc})"

    node_count = len(workflow.get("nodes", []))
    link_count = len(workflow.get("links", []))
    version = workflow.get("version", "unknown")
    return f"workflow found ({node_count} nodes, {link_count} links, version {version})"


def metadata_to_markdown(input_file: Path, payload: list[dict]) -> str:
    lines = [
        f"# Metadata: {input_file.name}",
        "",
        f"- **Source file**: `{input_file}`",
        "",
    ]
    for group in payload:
        lines.append("## Tags")
        lines.append("")
        for key, value in group.items():
            if key == "SourceFile":
                continue
            if isinstance(value, list):
                value = ", ".join(str(item) for item in value)
            lines.append(f"- **{key}**: {value}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def extract_metadata(
    exiftool: Path,
    input_file: Path,
    output_file: Path,
    export_ext: str,
    export_label: str,
) -> None:
    if export_label == COMFYUI_WORKFLOW_EXPORT:
        metadata = read_metadata_dict(exiftool, input_file)
        workflow = extract_comfyui_workflow(metadata)
        output_file.write_text(
            json.dumps(workflow, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return

    if export_ext == ".json":
        raw = run_exiftool(exiftool, ["-json", "-G", str(input_file)])
        output_file.write_text(raw, encoding="utf-8")
        return

    if export_ext == ".txt":
        raw = run_exiftool(exiftool, ["-G", str(input_file)])
        output_file.write_text(raw, encoding="utf-8")
        return

    if export_ext == ".html":
        raw = run_exiftool(
            exiftool,
            ["-htmlFormat", "-G", "-charset", "utf8", str(input_file)],
        )
        output_file.write_text(raw, encoding="utf-8")
        return

    if export_ext == ".md":
        raw = run_exiftool(exiftool, ["-json", "-G", str(input_file)])
        payload = json.loads(raw)
        output_file.write_text(
            metadata_to_markdown(input_file, payload),
            encoding="utf-8",
        )
        return

    raise ValueError(f"Unsupported export format: {export_ext}")


def format_dry_run_report(plan: JobPlan, exiftool: Path | None = None) -> str:
    lines = [
        "Dry Run Summary",
        "===============",
        f"Source: {plan.source_label}",
        f"File type: {plan.file_ext}",
        f"Files to process: {len(plan.input_files)}",
        f"Output folder: {plan.output_dir}",
        f"Export format: {plan.export_label}",
        "",
        "Planned outputs:",
    ]

    for input_file in plan.input_files:
        output_file = plan.output_path_for(input_file)
        status = "exists (will overwrite)" if output_file.exists() else "new file"
        line = f"  - {input_file.name} -> {output_file.name} [{status}]"
        if plan.export_label == COMFYUI_WORKFLOW_EXPORT and exiftool:
            try:
                metadata = read_metadata_dict(exiftool, input_file)
                line += f" | {preview_comfyui_workflow(metadata)}"
            except Exception as exc:  # noqa: BLE001 - dry-run should stay informative
                line += f" | metadata check failed ({exc})"
        lines.append(line)

    return "\n".join(lines) + "\n"


def file_dialog_types(file_ext: str) -> list[tuple[str, str]]:
    labels = {
        ".png": "PNG images",
        ".webp": "WebP images",
        ".mp3": "MP3 audio",
        ".mp4": "MP4 video",
    }
    label = labels.get(file_ext, file_ext.upper().strip(".") + " files")
    return [(label, f"*{file_ext}"), ("All files", "*.*")]

#Main section you need to worry about ;p
class MetadataExtractorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("EZ Metadata Extractor")
        self.root.minsize(780, 700)

        settings = load_settings()

        self.source_mode = tk.StringVar(value="file")
        self.source_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.file_type = tk.StringVar(value="WebP (.webp)")
        self.export_format = tk.StringVar(value="JSON (.json)")
        self.exiftool_dir = tk.StringVar(value=settings.get("exiftool_dir", ""))

        self._build_ui()
        self._show_exiftool_status()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

#Title lable
        ttk.Label(
            frame,
            text="Metadata Extractor",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor=tk.W)

# Description lable
        ttk.Label(
            frame,
            text=(
                "Extract metadata from images, audio, and video using ExifTool. "
                "ComfyUI Workflow export pulls embedded workflow JSON from ComfyUI images!"
            ),
        ).pack(anchor=tk.W, pady=(0, 10))

# Exif Tool folder location Section
        exiftool_box = ttk.LabelFrame(frame, text="ExifTool Location", padding=10)
        exiftool_box.pack(fill=tk.X, pady=(0, 10))

# Exif Tool Folder Title
        ttk.Label(
            exiftool_box,
            text="Folder containing exiftool.exe (or exiftool(-k).exe)",
        ).grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(exiftool_box, textvariable=self.exiftool_dir).grid(
            row=1, column=0, sticky=tk.EW, pady=(4, 0)
        )
        ttk.Button(
            exiftool_box,
            text="Browse...",
            command=self._browse_exiftool,
        ).grid(row=1, column=1, padx=(8, 0), pady=(4, 0))
        exiftool_box.columnconfigure(0, weight=1)

        self.exiftool_status = ttk.Label(exiftool_box, text="")
        self.exiftool_status.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(8, 0))

#Input Source Title
        source_box = ttk.LabelFrame(frame, text="Input Source", padding=10)
        source_box.pack(fill=tk.X, pady=(0, 10))

#File Type Description
        ttk.Label(source_box, text="File type to process").grid(
            row=0, column=0, sticky=tk.W
        )
        file_type_combo = ttk.Combobox(
            source_box,
            textvariable=self.file_type,
            values=list(FILE_EXTENSIONS.keys()),
            state="readonly",
        )
        file_type_combo.grid(row=1, column=0, sticky=tk.EW, pady=(4, 8))
        file_type_combo.bind("<<ComboboxSelected>>", self._on_file_type_change)

#Single File Selection
        ttk.Radiobutton(
            source_box,
            text="Single file",
            variable=self.source_mode,
            value="file",
            command=self._on_source_mode_change,
        ).grid(row=2, column=0, sticky=tk.W)

#Batch File Selection
        ttk.Radiobutton(
            source_box,
            text="All matching files in folder",
            variable=self.source_mode,
            value="folder",
            command=self._on_source_mode_change,
        ).grid(row=3, column=0, sticky=tk.W, pady=(4, 0))

#Browse Files
        self.source_entry = ttk.Entry(source_box, textvariable=self.source_path)
        self.source_entry.grid(row=4, column=0, sticky=tk.EW, pady=(8, 0))
        ttk.Button(
            source_box,
            text="Browse...",
            command=self._browse_source,
        ).grid(row=4, column=1, padx=(8, 0), pady=(8, 0))
        source_box.columnconfigure(0, weight=1)



#Output Section
        output_box = ttk.LabelFrame(frame, text="Output", padding=10)
        output_box.pack(fill=tk.X, pady=(0, 10))

#Output Folder
        ttk.Label(output_box, text="Output folder").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(output_box, textvariable=self.output_path).grid(
            row=1, column=0, sticky=tk.EW, pady=(4, 0)
        )
        ttk.Button(
            output_box,
            text="Browse...",
            command=self._browse_output,
        ).grid(row=1, column=1, padx=(8, 0), pady=(4, 0))

#Output Format dropdown box
        ttk.Label(output_box, text="Export format").grid(
            row=2, column=0, sticky=tk.W, pady=(10, 0)
        )
        ttk.Combobox(
            output_box,
            textvariable=self.export_format,
            values=list(EXPORT_FORMATS.keys()),
            state="readonly",
        ).grid(row=3, column=0, sticky=tk.EW, pady=(4, 0))
        output_box.columnconfigure(0, weight=1)

        button_row = ttk.Frame(frame)
        button_row.pack(fill=tk.X, pady=(0, 10))

#Processing Buttons
        ttk.Button(button_row, text="Dry Run", command=self._dry_run).pack(side=tk.LEFT)
        ttk.Button(button_row, text="Process", command=self._process).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        ttk.Button(button_row, text="Exit", command=self._on_exit).pack(side=tk.RIGHT)

#Activity Log
        log_box = ttk.LabelFrame(frame, text="Activity Log", padding=10)
        log_box.pack(fill=tk.BOTH, expand=True)

        self.log = scrolledtext.ScrolledText(
            log_box,
            height=14,
            wrap=tk.WORD,
            font=("Consolas", 10),
        )
        self.log.pack(fill=tk.BOTH, expand=True)
        self.log.configure(state=tk.DISABLED)

#Console welcome toast
        self._append_log("Ready! Choose ExifTool location, input, output, and formats.\n")
        self._append_log("Large folders take a while to process!\n")

    def _persist_exiftool_dir(self) -> None:
        save_settings({"exiftool_dir": self.exiftool_dir.get().strip()})

    def _show_exiftool_status(self) -> None:
        try:
            exiftool = find_exiftool_in_dir(self.exiftool_dir.get())
            version = run_exiftool(exiftool, ["-ver"]).strip().splitlines()[0]
            self.exiftool_status.configure(
                text=f"Using: {exiftool.name} (v{version})",
                foreground="#15803d",
            )
        except Exception as exc:  # noqa: BLE001 - surface setup errors in UI
            self.exiftool_status.configure(
                text=str(exc),
                foreground="#b91c1c",
            )

    def _append_log(self, text: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, text)
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _current_file_ext(self) -> str:
        return FILE_EXTENSIONS[self.file_type.get()]

    def _on_file_type_change(self, _event: object = None) -> None:
        self.source_path.set("")

    def _on_source_mode_change(self) -> None:
        self.source_path.set("")

    def _browse_exiftool(self) -> None:
        selected = filedialog.askdirectory(title="Select ExifTool folder")
        if selected:
            self.exiftool_dir.set(selected)
            self._persist_exiftool_dir()
            self._show_exiftool_status()

    def _browse_source(self) -> None:
        file_ext = self._current_file_ext()
        if self.source_mode.get() == "file":
            selected = filedialog.askopenfilename(
                title=f"Select {file_ext} file",
                filetypes=file_dialog_types(file_ext),
            )
        else:
            selected = filedialog.askdirectory(
                title=f"Select folder with {file_ext} files"
            )

        if selected:
            self.source_path.set(selected)

    def _browse_output(self) -> None:
        selected = filedialog.askdirectory(title="Select output folder")
        if selected:
            self.output_path.set(selected)

    def _build_plan(self) -> JobPlan | None:
        try:
            return build_job_plan(
                self.source_mode.get(),
                self.source_path.get(),
                self.output_path.get(),
                self.export_format.get(),
                self.file_type.get(),
            )
        except ValueError as exc:
            messagebox.showwarning("Missing Information", str(exc))
            return None

    def _resolve_exiftool(self) -> Path | None:
        self._persist_exiftool_dir()
        try:
            exiftool = find_exiftool_in_dir(self.exiftool_dir.get())
            self._show_exiftool_status()
            return exiftool
        except FileNotFoundError as exc:
            messagebox.showerror("ExifTool Required", str(exc))
            self._show_exiftool_status()
            return None

    def _resolve_exiftool_silent(self) -> Path | None:
        try:
            return find_exiftool_in_dir(self.exiftool_dir.get())
        except FileNotFoundError:
            return None

    def _dry_run(self) -> None:
        if not self._resolve_exiftool():
            return

        plan = self._build_plan()
        if not plan:
            return
        self._append_log("\n" + format_dry_run_report(plan, self._resolve_exiftool_silent()))

    def _process(self) -> None:
        exiftool = self._resolve_exiftool()
        if not exiftool:
            return

        plan = self._build_plan()
        if not plan:
            return

        self._append_log("\nProcessing...\n")
        success_count = 0
        errors: list[str] = []

        for input_file in plan.input_files:
            output_file = plan.output_path_for(input_file)
            try:
                extract_metadata(
                    exiftool,
                    input_file,
                    output_file,
                    plan.export_ext,
                    plan.export_label,
                )
                success_count += 1
                self._append_log(f"OK  {input_file.name} -> {output_file.name}\n")
            except Exception as exc:  # noqa: BLE001 - show per-file errors in UI
                errors.append(f"{input_file.name}: {exc}")
                self._append_log(f"ERR {input_file.name}: {exc}\n")

        self._append_log(
            f"\nFinished: {success_count}/{len(plan.input_files)} files processed.\n"
        )

        if errors:
            messagebox.showwarning(
                "Completed with errors",
                f"Processed {success_count} of {len(plan.input_files)} files.\n\n"
                + "\n".join(errors[:5])
                + ("\n..." if len(errors) > 5 else ""),
            )
        else:
            messagebox.showinfo(
                "Complete",
                f"Successfully exported metadata for {success_count} file(s).\n\n"
                f"Output folder:\n{plan.output_dir}",
            )

    def _on_exit(self) -> None:
        self._persist_exiftool_dir()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    try:
        try:
            ttk.Style().theme_use("vista")
        except tk.TclError:
            pass
        MetadataExtractorApp(root)
        root.deiconify()
        root.lift()
        root.attributes("-topmost", True)
        root.after(200, lambda: root.attributes("-topmost", False))
        root.mainloop()
    except Exception as exc:
        messagebox.showerror("Startup Error", str(exc))
        raise


if __name__ == "__main__":
    main()
