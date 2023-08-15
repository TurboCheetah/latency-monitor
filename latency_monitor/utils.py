import re
from typing import Dict, Union


def parse_mtr(output: str, target_ip: str) -> Dict[str, Union[float, int]]:
    """
    Extracts the latency values, loss percentage,
    and sent packets count for a specific target IP from the MTR output.

    Parameters:
    - output (str): The MTR command output.
    - target_ip (str): The target IP to search for.

    Returns:
    - dict: A dictionary containing the latency values, loss percentage,
            and sent packets count for the target IP,
            or None if the IP isn't found.
    """

    regex = re.compile(
        rf"{re.escape(target_ip)}\s+"
        r"(?P<Loss>\S+)%\s+"
        r"(?P<Snt>\d+)\s+"
        r"(?P<Last>[\d.]+)\s+"
        r"(?P<Avg>[\d.]+)\s+"
        r"(?P<Best>[\d.]+)\s+"
        r"(?P<Worst>[\d.]+)\s+"
        r"(?P<StDev>[\d.]+)"
    )

    match = regex.search(output)

    if not match:
        raise ValueError(f"Target IP {target_ip} not found in MTR output.")

    return {
        "loss": float(match.group("Loss")),
        "snt": int(match.group("Snt")),
        "last": float(match.group("Last")),
        "avg": float(match.group("Avg")),
        "best": float(match.group("Best")),
        "worst": float(match.group("Worst")),
        "stdev": float(match.group("StDev")),
    }
