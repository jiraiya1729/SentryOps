import logging
import asyncio
import threading
from concurrent import futures
import grpc

from opentelemetry.proto.collector.trace.v1 import trace_service_pb2, trace_service_pb2_grpc
from opentelemetry.proto.collector.metrics.v1 import metrics_service_pb2, metrics_service_pb2_grpc
from opentelemetry.proto.collector.logs.v1 import logs_service_pb2, logs_service_pb2_grpc

from app.otel.trace_processor import process_trace_request
from app.otel.metric_prpocessor import proces_metrics_reqeust

logger = logging.getLogger(__name__)


class TraceServicer(trace_service_pb2_grpc.TraceServiceServicer):
    def Export(self, request, context):
        try:
            span_count = process_trace_request(request)
            logger.debug(f"Received {span_count} spans via OTLP")
        except Exception as e:
            logger.error(f"Failed to process trace export: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
        return trace_service_pb2.ExportTraceServiceResponse()


class MetricServer(metrics_service_pb2_grpc.MetricsServiceServicer):
    def Export(self, request, context):
        try:
            metrics_count = proces_metrics_reqeust(request)
            logger.debug(f"Received {metrics_count} metrics data points via OTLP")
        except Exception as e:
            logger.error(f"Failed to process metrics export: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
        return metrics_service_pb2.ExportMetricsServiceResponse()


class LogsServicer(logs_service_pb2_grpc.LogsServiceServicer):
    def Export(self, request, context):
        logger.debug("Received logs via OTLP")
        return logs_service_pb2.ExportLogsServiceResponse()


_server: grpc.Server | None = None
_server_thread: threading.Thread | None = None


def _build_and_start_server(port: int):
    global _server
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=4),
        options=[
            ("grpc.max_receive_message_length", 16 * 1024 * 1024),
            ("grpc.max_send_message_length", 16 * 1024 * 1024),
        ],
    )
    trace_service_pb2_grpc.add_TraceServiceServicer_to_server(TraceServicer(), server)
    metrics_service_pb2_grpc.add_MetricsServiceServicer_to_server(MetricServer(), server)
    logs_service_pb2_grpc.add_LogsServiceServicer_to_server(LogsServicer(), server)
    result = server.add_insecure_port(f"[::]:{port}")
    if result == 0:
        logger.warning(f"OTLP gRPC server could not bind port {port} — OTLP disabled")
        return
    server.start()
    _server = server
    logger.info(f"OTLP gRPC server started on port {port}")


async def start_otlp_server(port: int = 4317):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _build_and_start_server, port)


async def stop_otlp_server():
    global _server
    if _server:
        _server.stop(grace=5)
        _server = None
        logger.info("OTLP gRPC server stopped")


