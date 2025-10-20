from typing import Optional


class Redaction(object):
    def __init__(
        self, start: int, end: int, text: str, info: str, color: Optional[str] = None
    ):
        """Create a new redaction.

        :param start: Start index of redaction
        :param end: End index of redaction
        :param text: Replacement text to use instead of underlying span
        """
        self.start = start
        self.end = end
        self.text = text
        self.info = info
        self.color = color

    def __json__(self):
        json = {
            "start": self.start,
            "end": self.end,
            "content": self.text,
            "extent": len(self.text),
            "type": "redaction",
            "info": self.info,
        }
        if self.color:
            json["format"] = {"color": self.color}
        return json

    def __eq__(self, __value: object) -> bool:
        """Compare this redaction to another object."""
        return repr(self) == repr(__value)

    def __repr__(self) -> str:
        return f"Redaction({self.start}, {self.end}, {self.text}, {self.info}, {self.color})"
