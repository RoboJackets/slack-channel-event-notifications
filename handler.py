"""
Post a notification in Slack when a channel is created or modified
"""

from os import environ

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import LambdaFunctionUrlResolver, Response
from aws_lambda_powertools.event_handler.middlewares import NextMiddleware
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext

from slack_sdk import WebClient
from slack_sdk.signature import SignatureVerifier


SLACK_SIGNING_SECRET = environ["SLACK_SIGNING_SECRET"]
SLACK_API_TOKEN = environ["SLACK_API_TOKEN"]
SLACK_NOTIFY_CHANNEL = environ["SLACK_NOTIFY_CHANNEL"]


def verify_slack_signature(  # pylint: disable=redefined-outer-name
    app: LambdaFunctionUrlResolver,
    next_middleware: NextMiddleware,
) -> Response:  # type: ignore
    """
    Verify the Slack signature on an incoming request
    """
    verifier = SignatureVerifier(SLACK_SIGNING_SECRET)

    if not verifier.is_valid_request(
        app.current_event.body, app.current_event.headers  # type: ignore
    ):
        return Response(
            status_code=401, content_type="text/plain", body="invalid signature"
        )

    return next_middleware(app)


tracer = Tracer()
logger = Logger()
app = LambdaFunctionUrlResolver()


@app.post("/slack", middlewares=[verify_slack_signature])
@tracer.capture_method
def handle_slack_event() -> Response:  # type: ignore
    """
    Handle an incoming event from Slack
    """
    slack = WebClient(token=SLACK_API_TOKEN)

    logger.info("Received Slack event", body=app.current_event.json_body)

    if app.current_event.json_body["type"] == "url_verification":
        return Response(
            status_code=200,
            content_type="text/plain",
            body=app.current_event.json_body["challenge"],
        )

    if app.current_event.json_body["type"] == "event_callback":

        if app.current_event.json_body["event"]["type"] == "channel_created":
            slack.chat_postMessage(
                channel=SLACK_NOTIFY_CHANNEL,
                text="<@"
                + app.current_event.json_body["event"]["channel"]["creator"]
                + "> created <#"
                + app.current_event.json_body["event"]["channel"]["id"]
                + ">",
            )
            return Response(status_code=200, content_type="text/plain", body="accepted")

        if app.current_event.json_body["event"]["type"] == "channel_archive":
            slack.chat_postMessage(
                channel=SLACK_NOTIFY_CHANNEL,
                text="<@"
                + app.current_event.json_body["event"]["user"]
                + "> archived <#"
                + app.current_event.json_body["event"]["channel"]
                + ">",
            )
            return Response(status_code=200, content_type="text/plain", body="accepted")

        if app.current_event.json_body["event"]["type"] == "channel_unarchive":
            slack.chat_postMessage(
                channel=SLACK_NOTIFY_CHANNEL,
                text="<@"
                + app.current_event.json_body["event"]["user"]
                + "> unarchived <#"
                + app.current_event.json_body["event"]["channel"]
                + ">",
            )
            return Response(status_code=200, content_type="text/plain", body="accepted")

        if app.current_event.json_body["event"]["type"] == "channel_rename":
            slack.chat_postMessage(
                channel=SLACK_NOTIFY_CHANNEL,
                text="<#"
                + app.current_event.json_body["event"]["channel"]["id"]
                + "> was renamed",
            )
            return Response(status_code=200, content_type="text/plain", body="accepted")

    return Response(
        status_code=400, content_type="text/plain", body="unexpected event type"
    )


@app.get("/ping")
@tracer.capture_method
def ping() -> Response:  # type: ignore
    """
    Return an arbitrary successful response, for health checks
    """
    return Response(status_code=200, content_type="text/plain", body="pong")


@app.get("/robots.txt")
@tracer.capture_method
def ping() -> Response:  # type: ignore
    """
    Return a robots.txt file
    """
    return Response(
        status_code=200, content_type="text/plain", body="User-agent: *\nDisallow: /"
    )


@logger.inject_lambda_context(correlation_id_path=correlation_paths.LAMBDA_FUNCTION_URL)
@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext) -> dict:  # type: ignore
    """
    Main Lambda event handler
    """
    return app.resolve(event, context)
