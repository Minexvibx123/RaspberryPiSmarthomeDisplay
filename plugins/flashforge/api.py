"""Documented Flashforge raw TCP client (port 8899)."""
from __future__ import annotations

import re
import socket


class FlashforgeClient:
    def __init__(self, host: str = "192.168.178.112", port: int = 8899, timeout: float = 5) -> None:
        self.host, self.port, self.timeout = host, port, timeout

    def command(self, command: str) -> str:
        responses = self._run([command])
        return responses[-1] if responses else ""

    def move(self, dx: float = 0.0, dy: float = 0.0, dz: float = 0.0, feed_rate: float = 1500.0) -> str:
        axes = []
        if dx: axes.append(f"X{dx:g}")
        if dy: axes.append(f"Y{dy:g}")
        if dz: axes.append(f"Z{dz:g}")
        if not axes:
            return ""
        self._run(["G91", f"G1 {' '.join(axes)} F{feed_rate:g}", "G90"])
        return "ok"

    def home(self) -> str:
        self._run(["G28"])
        return "ok"

    def status(self) -> dict[str, object]:
        machine = self.command("M119")
        progress = self.command("M27")
        temperatures = self.command("M105")
        status = re.search(r"MachineStatus:\s*(\S+)", machine)
        bytes_match = re.search(r"SD printing byte\s+(\d+)/(\d+)", progress)
        nozzle = re.search(r"T0:\s*([\d.]+)/([\d.]+)", temperatures)
        bed = re.search(r"B:\s*([\d.]+)/([\d.]+)", temperatures)
        return {"status": status.group(1) if status else "UNKNOWN", "progress": round(100 * int(bytes_match.group(1)) / int(bytes_match.group(2)), 1) if bytes_match and int(bytes_match.group(2)) else 0, "nozzle": tuple(map(float, nozzle.groups())) if nozzle else None, "bed": tuple(map(float, bed.groups())) if bed else None}

    def pause(self) -> str: return self.command("M25")
    def resume(self) -> str: return self.command("M24")
    def cancel(self) -> str: return self.command("M26")

    def _run(self, commands: list[str]) -> list[str]:
        """Acquire printer control once, send a command batch, release control."""
        responses = []
        with socket.create_connection((self.host, self.port), self.timeout) as connection:
            connection.settimeout(self.timeout)
            self._send(connection, "M601 S1")
            control = self._read(connection)
            if "Control Success" not in control:
                raise ConnectionError(f"Printer control unavailable: {control.strip()}")
            try:
                for command in commands:
                    self._send(connection, command)
                    responses.append(self._read(connection))
            finally:
                self._send(connection, "M602")
        return responses

    @staticmethod
    def _send(connection: socket.socket, command: str) -> None:
        connection.sendall(f"~{command}\r\n".encode())

    @staticmethod
    def _read(connection: socket.socket) -> str:
        data = b""
        while b"\nok\r\n" not in data and b"\nok\n" not in data:
            chunk = connection.recv(4096)
            if not chunk: break
            data += chunk
        return data.decode(errors="replace")