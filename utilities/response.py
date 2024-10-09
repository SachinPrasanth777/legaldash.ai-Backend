from fastapi import Response
from json import dumps


class JSONResponse(Response):
    def __init__(
        self,
        content: dict,
        media_type="application/json",
        status_code=200,
        *args,
        **kwargs
    ):
        super().__init__(
            content=dumps(content),
            media_type=media_type,
            status_code=status_code,
            *args,
            **kwargs
        )
