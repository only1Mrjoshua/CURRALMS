from datetime import datetime
from bson import ObjectId
from typing import Optional

class NotificationService:
    def __init__(self, db):
        self.collection = db.notifications
    
    async def create_lesson_notification(
        self, 
        user_id: str, 
        lesson_title: str, 
        course_title: str,
        notification_type: str = "lesson_created"
    ) -> dict:
        notification_data = {
            "user_id": user_id,
            "type": notification_type,
            "title": self._get_notification_title(notification_type, lesson_title),
            "message": self._get_notification_message(notification_type, lesson_title, course_title),
            "is_read": False,
            "created_at": datetime.utcnow(),
            "metadata": {
                "lesson_title": lesson_title,
                "course_title": course_title
            }
        }
        
        result = await self.collection.insert_one(notification_data)
        notification = await self.collection.find_one({"_id": result.inserted_id})
        if notification:
            notification["_id"] = str(notification["_id"])
        return notification
    
    def _get_notification_title(self, notification_type: str, lesson_title: str) -> str:
        titles = {
            "lesson_created": "New Lesson Available",
            "lesson_completed": "Lesson Completed",
            "lesson_updated": "Lesson Updated"
        }
        return titles.get(notification_type, "New Notification")
    
    def _get_notification_message(self, notification_type: str, lesson_title: str, course_title: str) -> str:
        messages = {
            "lesson_created": f"New lesson '{lesson_title}' has been added to '{course_title}'",
            "lesson_completed": f"You've completed the lesson '{lesson_title}' in '{course_title}'",
            "lesson_updated": f"The lesson '{lesson_title}' in '{course_title}' has been updated"
        }
        return messages.get(notification_type, "You have a new notification")