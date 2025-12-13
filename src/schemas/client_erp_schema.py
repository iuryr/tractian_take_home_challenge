CLIENT_WORKORDER_SCHEMA = {
        "title" : "Client ERP JSON Schema",
        "type" : "object",
        "properties": {
            "orderNo": {"type" : "integer"},
            "isActive": {"type" : "boolean"},
            "isCanceled": {"type" : "boolean"},
            "isDeleted": {"type" : "boolean"},
            "isDone": {"type" : "boolean"},
            "isOnHold": {"type" : "boolean"},
            "isPending": {"type" : "boolean"},
            "isSynced": {"type" : "boolean"},
            "summary": {"type" : "string"},
            "creationDate": {"type" : "string", "format" : "date-time"},
            "lastUpdateDate": {"type" : "string", "format" : "date-time"},
            "deletedDate": {"type" : ["string", "null"], "format" : "date-time"}
            },
        "required" : ["orderNo", "isActive", "isCanceled", "isDeleted", "isDone", "isOnHold", "isPending", "isSynced", "summary", "creationDate", "lastUpdateDate", "deletedDate"],
        "additionalProperties" : False
        }
