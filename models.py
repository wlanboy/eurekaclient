# models.py
from pydantic import BaseModel

class ClientConfig(BaseModel):
    serviceName: str
    healthEndpointPath: str
    infoEndpointPath: str
    httpPort: int
    securePort: int
    hostName: str
    dataCenterInfoName: str
    leaseInfo: dict = {
        "renewalIntervalInSecs": 30,
        "durationInSecs": 90
    }
