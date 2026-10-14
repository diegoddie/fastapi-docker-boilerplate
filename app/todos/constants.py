"""The todos package constants."""

TITLE_MAX_LENGTH = 200
DESCRIPTION_MAX_LENGTH = 2000

CAN_CREATE_TODO = "can_create_todo"
CAN_VIEW_TODO = "can_view_todo"
CAN_EDIT_TODO = "can_edit_todo"
CAN_DELETE_TODO = "can_delete_todo"
# Why: without it a user only reaches their own todos; with it, everyone's.
CAN_MANAGE_ALL_TODOS = "can_manage_all_todos"
