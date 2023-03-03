# import logging
# from typing import Awaitable, Callable

# from fastapi import Request, Response
# from opencensus.ext.azure.trace_exporter import AzureExporter
# from opencensus.trace.samplers import ProbabilitySampler
# from opencensus.trace.span import SpanKind
# from opencensus.trace.tracer import Tracer

# from pctasks.server.constants import (
#     DIMENSION_KEYS,
#     HTTP_METHOD,
#     HTTP_PATH,
#     HTTP_STATUS_CODE,
#     HTTP_URL,
#     X_AZURE_CLIENTIP,
#     X_AZURE_REF,
#     X_FORWARDED_FOR,
#     X_ORIGINAL_FORWARDED_FOR,
#     X_REQUEST_ENTITY,
# )
# from pctasks.server.request import ParsedRequest
# from pctasks.server.settings import ServerSettings

# logger = logging.getLogger(__name__)


# def get_request_ip(request: Request) -> str:
#     """Gets the IP address of the request."""

#     ip_header = (
#         request.headers.get(X_AZURE_CLIENTIP)  # set by Front Door
#         or request.headers.get(X_ORIGINAL_FORWARDED_FOR)
#         or request.headers.get(X_FORWARDED_FOR)
#     )

#     # If multiple IPs, take the last one
#     return ip_header.split(",")[-1] if ip_header else ""


# app_insights_instrumentation_key = \
# ServerSettings.get().app_insights_instrumentation_key
# exporter = (
#     AzureExporter(
#         connection_string=(f"InstrumentationKey={app_insights_instrumentation_key}")
#     )
#     if app_insights_instrumentation_key
#     else None
# )

# is_trace_enabled = exporter is not None


# async def trace_request(
#     service_name: str,
#     request: Request,
#     call_next: Callable[[Request], Awaitable[Response]],
# ) -> Response:
#     """Construct a request trace with custom dimensions"""
#     parsed_request = ParsedRequest(request)
#     request_path = parsed_request.path.strip("/")

#     if _should_trace_request(request):
#         workflow_info = parsed_request.workflow_info
#         tracer = Tracer(
#             exporter=exporter,
#             sampler=ProbabilitySampler(1.0),
#         )
#         with tracer.span("main") as span:
#             span.span_kind = SpanKind.SERVER

#             # Throwing the main span into request state lets us create child spans
#             # in downstream request processing, if there are specific things that
#             # are slow.
#             request.state.parent_span = span

#             # Add request dimensions to the trace prior to calling the next middleware
#             tracer.add_attribute_to_current_span(
#                 attribute_key="ref_id",
#                 attribute_value=request.headers.get(X_AZURE_REF),
#             )
#             tracer.add_attribute_to_current_span(
#                 attribute_key="request_entity",
#                 attribute_value=request.headers.get(X_REQUEST_ENTITY),
#             )
#             tracer.add_attribute_to_current_span(
#                 attribute_key="request_ip",
#                 attribute_value=get_request_ip(request),
#             )
#             tracer.add_attribute_to_current_span(
#                 attribute_key=HTTP_METHOD, attribute_value=str(request.method)
#             )
#             tracer.add_attribute_to_current_span(
#                 attribute_key=HTTP_URL, attribute_value=str(request.url)
#             )
#             tracer.add_attribute_to_current_span(
#                 attribute_key=HTTP_PATH, attribute_value=request_path
#             )
#             tracer.add_attribute_to_current_span(
#                 attribute_key="service", attribute_value=service_name
#             )
#             tracer.add_attribute_to_current_span(
#                 attribute_key="in-server", attribute_value="true"
#             )
#             if workflow_info:
#                 tracer.add_attribute_to_current_span(
#                     attribute_key=DIMENSION_KEYS.WORKFLOW_ID,
#                     attribute_value=workflow_info.workflow_id,
#                 )
#                 if workflow_info.run_id:
#                     tracer.add_attribute_to_current_span(
#                         attribute_key=DIMENSION_KEYS.RUN_ID,
#                         attribute_value=workflow_info.run_id,
#                     )

#             # Call next middleware
#             response = await call_next(request)

#             # Include response dimensions in the trace
#             tracer.add_attribute_to_current_span(
#                 attribute_key=HTTP_STATUS_CODE, attribute_value=response.status_code
#             )
#         return response
#     else:
#         return await call_next(request)


# def _should_trace_request(request: Request) -> bool:
#     """
#     Determine if we should trace a request.
#         - Not a HEAD request
#         - Not a health check endpoint
#     """
#     return (
#         is_trace_enabled
#         and request.method.lower() != "head"
#         and not request.url.path.strip("/").endswith("_mgmt/ping")
#     )
