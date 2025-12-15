from models.customer_system_models import CustomerSystemWorkorder
from models.tracOS_models import TracOSWorkorder, TracOSStatus

def customer_bool_to_tracos_status(customer_obj: CustomerSystemWorkorder) -> TracOSStatus:
    """Map customer object boolean to tracOS object literal"""
    if customer_obj.isActive:
        return "in_progress"
    if customer_obj.isCanceled or customer_obj.isDeleted:
        return "cancelled"
    if customer_obj.isPending:
        return "pending"
    if customer_obj.isDone:
        return "completed"
    if customer_obj.isOnHold:
        return "on_hold"
    raise ValueError("Invalid customer workorder status")

def client_to_tracos(left: CustomerSystemWorkorder) -> TracOSWorkorder:
    return TracOSWorkorder(
                _id = None,
                number = left.orderNo,
                status = customer_bool_to_tracos_status(left),
                title = f"Example workorder #{left.orderNo}",
                description = left.summary,
                createdAt = left.creationDate,
                updatedAt = left.lastUpdateDate,
                deleted = left.isDeleted,
                deletedAt = left.deletedDate,
                isSynced = left.isSynced, #are we sure?
                syncedAt = None
                )

def tracos_to_client(left: TracOSWorkorder) ->  CustomerSystemWorkorder:
    return CustomerSystemWorkorder(
            orderNo= left.number,
            isActive= left.status == "in_progress",
            isCanceled = left.status == "cancelled",
            isDeleted = left.deleted,
            isDone = left.status == "completed",
            isOnHold = left.status == "on_hold",
            isPending = left.status == "pending",
            isSynced = True,
            summary = left.description,
            creationDate=left.createdAt,
            lastUpdateDate=left.updatedAt,
            deletedDate=left.deletedAt
            )
