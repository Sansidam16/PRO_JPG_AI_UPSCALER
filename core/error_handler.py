"""Utilitas penanganan error agar pesan di log konsisten dan informatif."""


class PipelineError(RuntimeError):
    """Kesalahan yang sudah dikenali pada pipeline pemrosesan gambar."""


def describe(exc):
    """Format singkat namun informatif untuk pesan log."""
    return f"{type(exc).__name__}: {exc}"
