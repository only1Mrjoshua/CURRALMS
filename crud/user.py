# crud/user.py
from typing import List, Optional
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime

from models.user import User, RoleEnum
from schemas.user import UserCreate
from utils.security import hash_password

class UserCRUD:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def _is_connected(self):
        try:
            await self.db.command('ping')
            return True
        except:
            return False

    def _convert_objectids_to_strings(self, data: dict) -> dict:
        if not data:
            return data
            
        converted = data.copy()
        
        if '_id' in converted and converted['_id']:
            converted['id'] = str(converted['_id'])
            del converted['_id']
        
        for key in ['invited_by']:
            if key in converted and converted[key] and isinstance(converted[key], ObjectId):
                converted[key] = str(converted[key])
        
        return converted

    async def get_user_by_email(self, email: str) -> Optional[User]:
        if not await self._is_connected():
            return None
            
        try:
            user_data = await self.db.users.find_one({"email": email.lower()})
            if user_data:
                user_data = self._convert_objectids_to_strings(user_data)
                return User(**user_data)
            return None
        except Exception as e:
            print(f"Error getting user by email: {e}")
            return None

    async def get_user_by_username(self, username: str) -> Optional[User]:
        if not await self._is_connected():
            return None
            
        try:
            user_data = await self.db.users.find_one({"username": username})
            if user_data:
                user_data = self._convert_objectids_to_strings(user_data)
                return User(**user_data)
            return None
        except Exception as e:
            print(f"Error getting user by username: {e}")
            return None

    async def get_user_by_identifier(self, identifier: str) -> Optional[User]:
        user = await self.get_user_by_email(identifier)
        if not user:
            user = await self.get_user_by_username(identifier)
        return user

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        if not await self._is_connected():
            return None
            
        try:
            user_data = await self.db.users.find_one({"_id": ObjectId(user_id)})
            if user_data:
                user_data = self._convert_objectids_to_strings(user_data)
                return User(**user_data)
            return None
        except Exception as e:
            print(f"Error getting user by ID: {e}")
            return None

    async def create_user(self, user_data: UserCreate, avatar_url: str = None, invited_by: str = None) -> Optional[User]:
        if not await self._is_connected():
            return None
            
        try:
            # Check if user already exists
            existing_email = await self.get_user_by_email(user_data.email)
            existing_username = await self.get_user_by_username(user_data.username)
            if existing_email or existing_username:
                return None

            # Determine role (first user becomes admin)
            user_count = await self.db.users.count_documents({})
            role = RoleEnum.admin if user_count == 0 else user_data.role

            user_dict = user_data.model_dump(exclude={"password"})
            user_dict["password_hash"] = hash_password(user_data.password)
            user_dict["role"] = role
            user_dict["avatar_url"] = avatar_url
            user_dict["invited_by"] = ObjectId(invited_by) if invited_by else None
            user_dict["created_at"] = datetime.utcnow()
            user_dict["is_active"] = True

            result = await self.db.users.insert_one(user_dict)
            created_user = await self.db.users.find_one({"_id": result.inserted_id})
            
            if created_user:
                created_user = self._convert_objectids_to_strings(created_user)
                return User(**created_user)
            return None
        except Exception as e:
            print(f"Error creating user: {e}")
            return None

    async def update_user(self, user_id: str, update_data: dict) -> Optional[User]:
        if not await self._is_connected():
            return None
            
        try:
            # Check username uniqueness if updating username
            if "username" in update_data:
                existing = await self.get_user_by_username(update_data["username"])
                if existing and str(existing.id) != user_id:
                    return None

            update_data["updated_at"] = datetime.utcnow()
            
            result = await self.db.users.find_one_and_update(
                {"_id": ObjectId(user_id)},
                {"$set": update_data},
                return_document=True
            )
            
            if result:
                result = self._convert_objectids_to_strings(result)
                return User(**result)
            return None
        except Exception as e:
            print(f"Error updating user: {e}")
            return None

    async def update_last_login(self, user_id: str) -> bool:
        if not await self._is_connected():
            return False
            
        try:
            await self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"last_login": datetime.utcnow()}}
            )
            return True
        except Exception as e:
            print(f"Error updating last login: {e}")
            return False

    async def get_users(self, role: Optional[RoleEnum] = None) -> List[User]:
        if not await self._is_connected():
            return []
            
        try:
            query = {}
            if role:
                query["role"] = role
            
            cursor = self.db.users.find(query)
            users_data = await cursor.to_list(length=100)
            
            users = []
            for user_data in users_data:
                user_data = self._convert_objectids_to_strings(user_data)
                users.append(User(**user_data))
            
            return users
        except Exception as e:
            print(f"Error getting users: {e}")
            return []

    # NEW METHOD: Get users with resolved inviter names
    async def get_users_with_inviter_names(self, role: Optional[RoleEnum] = None) -> List[User]:
        """
        Get all users with resolved inviter usernames instead of IDs
        """
        if not await self._is_connected():
            return []
            
        try:
            query = {}
            if role:
                query["role"] = role
            
            cursor = self.db.users.find(query)
            users_data = await cursor.to_list(length=100)
            
            users = []
            for user_data in users_data:
                user_data = self._convert_objectids_to_strings(user_data)
                user = User(**user_data)
                
                # Resolve inviter username if exists
                if user.invited_by and user.invited_by != '—':
                    try:
                        inviter = await self.get_user_by_id(user.invited_by)
                        if inviter:
                            user.invited_by = inviter.username
                        else:
                            user.invited_by = "Unknown User"
                    except Exception as e:
                        print(f"Error resolving inviter for user {user.id}: {e}")
                        user.invited_by = "Error resolving"
                
                users.append(user)
            
            return users
        except Exception as e:
            print(f"Error getting users with inviter names: {e}")
            return []

    # ALTERNATIVE METHOD: Get inviter username for a single user
    async def get_inviter_username(self, invited_by_id: str) -> Optional[str]:
        """
        Get the username of the user who invited another user
        """
        if not invited_by_id or invited_by_id == '—':
            return None
            
        try:
            inviter = await self.get_user_by_id(invited_by_id)
            if inviter:
                return inviter.username
            return None
        except Exception as e:
            print(f"Error getting inviter username: {e}")
            return None

    async def delete_user(self, user_id: str) -> bool:
        if not await self._is_connected():
            return False
            
        try:
            result = await self.db.users.delete_one({"_id": ObjectId(user_id)})
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False