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
            print("✅ MongoDB connection is active")
            return True
        except Exception as e:
            print(f"❌ MongoDB connection failed: {e}")
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
        print(f"🔍 Looking up user by email: {email}")
        if not await self._is_connected():
            return None
            
        try:
            user_data = await self.db.users.find_one({"email": email.lower()})
            if user_data:
                user_data = self._convert_objectids_to_strings(user_data)
                print(f"✅ User found by email: {email}")
                return User(**user_data)
            print(f"❌ User not found by email: {email}")
            return None
        except Exception as e:
            print(f"❌ Error getting user by email: {e}")
            return None

    async def get_user_by_username(self, username: str) -> Optional[User]:
        print(f"🔍 Looking up user by username: {username}")
        if not await self._is_connected():
            return None
            
        try:
            user_data = await self.db.users.find_one({"username": username})
            if user_data:
                user_data = self._convert_objectids_to_strings(user_data)
                print(f"✅ User found by username: {username}")
                return User(**user_data)
            print(f"❌ User not found by username: {username}")
            return None
        except Exception as e:
            print(f"❌ Error getting user by username: {e}")
            return None

    async def get_user_by_identifier(self, identifier: str) -> Optional[User]:
        user = await self.get_user_by_email(identifier)
        if not user:
            user = await self.get_user_by_username(identifier)
        return user

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        print(f"🔍 Looking up user by ID: {user_id}")
        if not await self._is_connected():
            return None
            
        try:
            user_data = await self.db.users.find_one({"_id": ObjectId(user_id)})
            if user_data:
                user_data = self._convert_objectids_to_strings(user_data)
                print(f"✅ User found by ID: {user_id}")
                return User(**user_data)
            print(f"❌ User not found by ID: {user_id}")
            return None
        except Exception as e:
            print(f"❌ Error getting user by ID: {e}")
            return None

    async def create_user(self, user_data: UserCreate, avatar_url: str = None, invited_by: str = None) -> Optional[User]:
        print(f"🆕 Starting user creation process...")
        if not await self._is_connected():
            print("❌ Database not connected")
            return None
            
        try:
            # Check if user already exists
            existing_email = await self.get_user_by_email(user_data.email)
            existing_username = await self.get_user_by_username(user_data.username)
            
            if existing_email:
                print(f"❌ User with email already exists: {user_data.email}")
                return None
            if existing_username:
                print(f"❌ User with username already exists: {user_data.username}")
                return None

            # Determine role (first user becomes admin)
            user_count = await self.db.users.count_documents({})
            role = RoleEnum.admin if user_count == 0 else user_data.role
            print(f"📊 User count: {user_count}, assigned role: {role}")

            # FIX: Use dict() instead of model_dump() for Pydantic v1
            print(f"📝 Converting UserCreate to dict...")
            user_dict = user_data.dict(exclude={"password"})
            print(f"✅ UserCreate converted to dict successfully")
            
            user_dict["password_hash"] = hash_password(user_data.password)
            user_dict["role"] = role
            user_dict["avatar_url"] = avatar_url
            user_dict["invited_by"] = ObjectId(invited_by) if invited_by else None
            user_dict["created_at"] = datetime.utcnow()
            user_dict["last_login"] = datetime.utcnow()  # Add initial last login
            user_dict["is_active"] = True

            print(f"✅ Creating user with data keys: {list(user_dict.keys())}")
            print(f"📧 Email: {user_dict.get('email')}")
            print(f"👤 Username: {user_dict.get('username')}")
            print(f"🎭 Role: {user_dict.get('role')}")

            result = await self.db.users.insert_one(user_dict)
            print(f"✅ User inserted with ID: {result.inserted_id}")
            
            created_user = await self.db.users.find_one({"_id": result.inserted_id})
            
            if created_user:
                created_user = self._convert_objectids_to_strings(created_user)
                print(f"✅ User created successfully: {created_user['email']}")
                return User(**created_user)
            
            print("❌ Failed to retrieve created user from database")
            return None
            
        except Exception as e:
            print(f"❌ Error creating user: {str(e)}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            return None

    async def update_user(self, user_id: str, update_data: dict) -> Optional[User]:
        print(f"🔄 Updating user: {user_id}")
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
                print(f"✅ User updated successfully: {user_id}")
                return User(**result)
            return None
        except Exception as e:
            print(f"❌ Error updating user: {e}")
            return None

    async def update_last_login(self, user_id: str) -> bool:
        print(f"🔄 Updating last login for user: {user_id}")
        if not await self._is_connected():
            return False
            
        try:
            result = await self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"last_login": datetime.utcnow()}}
            )
            if result.modified_count > 0:
                print(f"✅ Last login updated for user: {user_id}")
                return True
            else:
                print(f"⚠️ No user found to update last login: {user_id}")
                return False
        except Exception as e:
            print(f"❌ Error updating last login: {e}")
            return False

    async def get_users(self, role: Optional[RoleEnum] = None) -> List[User]:
        print(f"🔍 Getting users list, role filter: {role}")
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
            
            print(f"✅ Retrieved {len(users)} users")
            return users
        except Exception as e:
            print(f"❌ Error getting users: {e}")
            return []

    # NEW METHOD: Get users with resolved inviter names
    async def get_users_with_inviter_names(self, role: Optional[RoleEnum] = None) -> List[User]:
        """
        Get all users with resolved inviter usernames instead of IDs
        """
        print(f"🔍 Getting users with inviter names, role filter: {role}")
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
            
            print(f"✅ Retrieved {len(users)} users with inviter names")
            return users
        except Exception as e:
            print(f"❌ Error getting users with inviter names: {e}")
            return []

    # ALTERNATIVE METHOD: Get inviter username for a single user
    async def get_inviter_username(self, invited_by_id: str) -> Optional[str]:
        """
        Get the username of the user who invited another user
        """
        print(f"🔍 Getting inviter username for: {invited_by_id}")
        if not invited_by_id or invited_by_id == '—':
            return None
            
        try:
            inviter = await self.get_user_by_id(invited_by_id)
            if inviter:
                print(f"✅ Found inviter: {inviter.username}")
                return inviter.username
            print(f"❌ Inviter not found: {invited_by_id}")
            return None
        except Exception as e:
            print(f"❌ Error getting inviter username: {e}")
            return None

    async def delete_user(self, user_id: str) -> bool:
        print(f"🗑️ Deleting user: {user_id}")
        if not await self._is_connected():
            return False
            
        try:
            result = await self.db.users.delete_one({"_id": ObjectId(user_id)})
            if result.deleted_count > 0:
                print(f"✅ User deleted successfully: {user_id}")
                return True
            else:
                print(f"❌ User not found for deletion: {user_id}")
                return False
        except Exception as e:
            print(f"❌ Error deleting user: {e}")
            return False