"""
Common utility functions for API responses
"""
from rest_framework.response import Response
from rest_framework import status


def success_response(data=None, message="Success", status_code=status.HTTP_200_OK):
    """
    Standard success response format matching Node.js API
    """
    response_data = {
        "code": 200,
        "msg": message,
        "data": data
    }
    return Response(response_data, status=status_code)


def error_response(message="Error", errors=None, status_code=status.HTTP_400_BAD_REQUEST):
    """
    Standard error response format matching Node.js API
    """
    response_data = {
        "code": status_code,
        "msg": message
    }
    if errors:
        response_data["errors"] = errors
    return Response(response_data, status=status_code)


def paginated_response(queryset, serializer_class, request, message="Success"):
    """
    Standard paginated response format
    """
    from rest_framework.pagination import PageNumberPagination
    
    paginator = PageNumberPagination()
    paginator.page_size = 20
    page = paginator.paginate_queryset(queryset, request)
    
    if page is not None:
        serializer = serializer_class(page, many=True)
        return paginator.get_paginated_response({
            "code": 200,
            "msg": message,
            "data": {
                "list": serializer.data,
                "page": {
                    "pageNum": paginator.page.number,
                    "pageSize": paginator.page_size,
                    "total": paginator.page.paginator.count,
                    "totalPages": paginator.page.paginator.num_pages
                }
            }
        })
    
    serializer = serializer_class(queryset, many=True)
    return success_response({
        "list": serializer.data,
        "page": {
            "pageNum": 1,
            "pageSize": len(serializer.data),
            "total": len(serializer.data),
            "totalPages": 1
        }
    }, message)