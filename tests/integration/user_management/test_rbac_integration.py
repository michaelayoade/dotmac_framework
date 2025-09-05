"""
Integration tests for user management v2 RBAC (Role-Based Access Control) system.
Tests complete role and permission management workflows.
"""
from collections.abc import AsyncGenerator
from uuid import UUID, uuid4

import pytest
from dotmac_management.user_management.models.rbac_models import (
    PermissionModel,
    PermissionScope,
    PermissionType,
    RoleModel,
)
from dotmac_management.user_management.models.user_models import UserModel
from dotmac_management.user_management.schemas.rbac_schemas import (
    PermissionCreateSchema,
    PermissionSearchSchema,
    RoleCategory,
    RoleCreateSchema,
    RoleSearchSchema,
)
from dotmac_management.user_management.schemas.user_schemas import UserCreateSchema, UserType
from dotmac_management.user_management.services.rbac_service import RBACService
from dotmac_management.user_management.services.user_service import UserService
from dotmac_shared.database.session import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for testing."""
    async with get_db_session() as session:
        yield session

@pytest.fixture
async def tenant_id() -> UUID:
    """Generate test tenant ID."""
    return uuid4()

@pytest.fixture
async def test_user(db_session: AsyncSession, tenant_id: UUID) -> UserModel:
    """Create test user."""
    user_service = UserService(db_session, tenant_id)
    user_data = UserCreateSchema(
        username="testuser",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        user_type=UserType.CUSTOMER,
        password="SecurePass123!",
        terms_accepted=True,
        privacy_accepted=True
    )
    user_response = await user_service.create_user(user_data)
    user = await user_service.user_repo.get_by_id(user_response.id)
    return user

@pytest.fixture
async def admin_user(db_session: AsyncSession, tenant_id: UUID) -> UserModel:
    """Create admin test user."""
    user_service = UserService(db_session, tenant_id)
    user_data = UserCreateSchema(
        username="adminuser",
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        user_type=UserType.ADMIN,
        password="AdminPass123!",
        terms_accepted=True,
        privacy_accepted=True
    )
    user_response = await user_service.create_user(user_data)
    user = await user_service.user_repo.get_by_id(user_response.id)
    return user

@pytest.fixture
async def test_permissions(db_session: AsyncSession, tenant_id: UUID) -> list[PermissionModel]:
    """Create test permissions."""
    rbac_service = RBACService(db_session, tenant_id)
    
    permissions_data = [
        PermissionCreateSchema(
            name="read:users",
            display_name="Read Users",
            description="Permission to read user information",
            permission_type=PermissionType.READ,
            scope=PermissionScope.USER,
            resource="users"
        ),
        PermissionCreateSchema(
            name="write:users",
            display_name="Write Users",
            description="Permission to create and update users",
            permission_type=PermissionType.WRITE,
            scope=PermissionScope.USER,
            resource="users"
        ),
        PermissionCreateSchema(
            name="delete:users",
            display_name="Delete Users", 
            description="Permission to delete users",
            permission_type=PermissionType.DELETE,
            scope=PermissionScope.USER,
            resource="users"
        ),
        PermissionCreateSchema(
            name="read:billing",
            display_name="Read Billing",
            description="Permission to read billing information",
            permission_type=PermissionType.READ,
            scope=PermissionScope.BILLING,
            resource="invoices"
        )
    ]
    
    permissions = []
    for perm_data in permissions_data:
        perm_response = await rbac_service.create_permission(perm_data)
        perm = await rbac_service.permission_repo.get_by_id(perm_response.id)
        permissions.append(perm)
    
    return permissions

@pytest.fixture  
async def test_role(
    db_session: AsyncSession, 
    tenant_id: UUID, 
    test_permissions: list[PermissionModel],
    admin_user: UserModel
) -> RoleModel:
    """Create test role with permissions."""
    rbac_service = RBACService(db_session, tenant_id)
    
    role_data = RoleCreateSchema(
        name="customer_user",
        display_name="Customer User",
        description="Standard customer user role",
        role_category=RoleCategory.USER,
        permission_ids=[p.id for p in test_permissions[:2]]  # read:users and write:users
    )
    
    role_response = await rbac_service.create_role(role_data, admin_user.id)
    role = await rbac_service.role_repo.get_by_id(role_response.id)
    return role

class TestRoleManagement:
    """Test role creation, management, and hierarchy."""
    
    async def test_create_role_with_permissions(
        self, 
        db_session: AsyncSession, 
        tenant_id: UUID,
        test_permissions: list[PermissionModel],
        admin_user: UserModel
    ):
        """Test creating a role with permissions."""
        rbac_service = RBACService(db_session, tenant_id)
        
        role_data = RoleCreateSchema(
            name="test_role",
            display_name="Test Role",
            description="A test role",
            role_category=RoleCategory.CUSTOM,
            permission_ids=[test_permissions[0].id, test_permissions[1].id]
        )
        
        role_response = await rbac_service.create_role(role_data, admin_user.id)
        
        assert role_response.name == "test_role"
        assert role_response.display_name == "Test Role"
        assert role_response.role_category == "custom"
        
        # Verify permissions were assigned
        role_details = await rbac_service.get_role_details(role_response.id)
        assert len(role_details.permissions) == 2
        permission_names = [p.name for p in role_details.permissions]
        assert "read:users" in permission_names
        assert "write:users" in permission_names

    async def test_create_role_hierarchy(
        self,
        db_session: AsyncSession,
        tenant_id: UUID,
        test_permissions: list[PermissionModel],
        admin_user: UserModel
    ):
        """Test creating parent-child role relationships."""
        rbac_service = RBACService(db_session, tenant_id)
        
        # Create parent role
        parent_role_data = RoleCreateSchema(
            name="parent_role",
            display_name="Parent Role",
            description="Parent role in hierarchy",
            role_category=RoleCategory.ADMIN,
            permission_ids=[test_permissions[0].id]
        )
        
        parent_role_response = await rbac_service.create_role(parent_role_data, admin_user.id)
        
        # Create child role
        child_role_data = RoleCreateSchema(
            name="child_role",
            display_name="Child Role",
            description="Child role in hierarchy",
            role_category=RoleCategory.USER,
            parent_role_id=parent_role_response.id,
            permission_ids=[test_permissions[1].id]
        )
        
        child_role_response = await rbac_service.create_role(child_role_data, admin_user.id)
        
        # Verify hierarchy
        parent_details = await rbac_service.get_role_details(parent_role_response.id)
        assert len(parent_details.child_roles) == 1
        assert parent_details.child_roles[0].name == "child_role"
        
        child_details = await rbac_service.get_role_details(child_role_response.id)
        assert child_details.parent_role is not None
        assert child_details.parent_role.name == "parent_role"

    async def test_role_search_and_filtering(
        self,
        db_session: AsyncSession,
        tenant_id: UUID,
        test_permissions: list[PermissionModel],
        admin_user: UserModel
    ):
        """Test role search functionality."""
        rbac_service = RBACService(db_session, tenant_id)
        
        # Create multiple roles for testing
        roles_data = [
            RoleCreateSchema(
                name="admin_role",
                display_name="Admin Role",
                description="Administrative role",
                role_category=RoleCategory.ADMIN,
                permission_ids=[p.id for p in test_permissions]
            ),
            RoleCreateSchema(
                name="user_role", 
                display_name="User Role",
                description="Basic user role",
                role_category=RoleCategory.USER,
                permission_ids=[test_permissions[0].id]
            ),
            RoleCreateSchema(
                name="custom_role",
                display_name="Custom Role",
                description="Custom business role",
                role_category=RoleCategory.CUSTOM
            )
        ]
        
        for role_data in roles_data:
            await rbac_service.create_role(role_data, admin_user.id)
        
        # Test search by query
        search_params = RoleSearchSchema(
            query="admin",
            page=1,
            page_size=10
        )
        
        roles, total_count = await rbac_service.search_roles(search_params)
        assert total_count >= 1
        admin_roles = [r for r in roles if "admin" in r.name.lower() or "admin" in r.display_name.lower()]
        assert len(admin_roles) >= 1
        
        # Test filter by category
        search_params = RoleSearchSchema(
            role_category=RoleCategory.USER,
            page=1,
            page_size=10
        )
        
        roles, total_count = await rbac_service.search_roles(search_params)
        assert all(r.role_category == "user" for r in roles)

    async def test_delete_role_validation(
        self,
        db_session: AsyncSession,
        tenant_id: UUID,
        test_role: RoleModel,
        test_user: UserModel
    ):
        """Test role deletion with proper validation."""
        rbac_service = RBACService(db_session, tenant_id)
        
        # Assign role to user
        await rbac_service.assign_role_to_user(test_user.id, test_role.id)
        
        # Try to delete role with active users - should fail
        with pytest.raises(ValueError, match="Cannot delete role with .* active users"):
            await rbac_service.delete_role(test_role.id)
        
        # Remove user from role
        await rbac_service.revoke_role_from_user(test_user.id, test_role.id)
        
        # Now deletion should succeed
        success = await rbac_service.delete_role(test_role.id)
        assert success is True

class TestPermissionManagement:
    """Test permission creation and management."""
    
    async def test_create_permission(
        self,
        db_session: AsyncSession,
        tenant_id: UUID,
        admin_user: UserModel
    ):
        """Test permission creation."""
        rbac_service = RBACService(db_session, tenant_id)
        
        perm_data = PermissionCreateSchema(
            name="manage:network",
            display_name="Manage Network",
            description="Permission to manage network settings",
            permission_type=PermissionType.ADMIN,
            scope=PermissionScope.NETWORK,
            resource="network_settings"
        )
        
        perm_response = await rbac_service.create_permission(perm_data, admin_user.id)
        
        assert perm_response.name == "manage:network"
        assert perm_response.permission_type == "admin"
        assert perm_response.scope == "network"
        assert perm_response.resource == "network_settings"

    async def test_permission_search(
        self,
        db_session: AsyncSession,
        tenant_id: UUID,
        test_permissions: list[PermissionModel]
    ):
        """Test permission search functionality."""
        rbac_service = RBACService(db_session, tenant_id)
        
        # Search by type
        search_params = PermissionSearchSchema(
            permission_type=PermissionType.READ,
            page=1,
            page_size=10
        )
        
        permissions, total_count = await rbac_service.search_permissions(search_params)
        assert all(p.permission_type == "read" for p in permissions)
        
        # Search by scope
        search_params = PermissionSearchSchema(
            scope=PermissionScope.USER,
            page=1,
            page_size=10
        )
        
        permissions, total_count = await rbac_service.search_permissions(search_params)
        assert all(p.scope == "user" for p in permissions)
        
        # Search by resource
        search_params = PermissionSearchSchema(
            resource="users",
            page=1,
            page_size=10
        )
        
        permissions, total_count = await rbac_service.search_permissions(search_params)
        assert all("users" in p.resource for p in permissions)

class TestRolePermissionAssignment:
    """Test role-permission relationship management."""
    
    async def test_assign_permission_to_role(
        self,
        db_session: AsyncSession,
        tenant_id: UUID,
        test_role: RoleModel,
        test_permissions: list[PermissionModel],
        admin_user: UserModel
    ):
        """Test assigning additional permissions to role."""
        rbac_service = RBACService(db_session, tenant_id)
        
        # Role should already have first 2 permissions from fixture
        role_details = await rbac_service.get_role_details(test_role.id)
        initial_perm_count = len(role_details.permissions)
        
        # Assign additional permission
        success = await rbac_service.assign_permission_to_role(
            role_id=test_role.id,
            permission_id=test_permissions[2].id,  # delete:users
            granted_by=admin_user.id
        )
        
        assert success is True
        
        # Verify permission was added
        updated_role_details = await rbac_service.get_role_details(test_role.id)
        assert len(updated_role_details.permissions) == initial_perm_count + 1
        
        permission_names = [p.name for p in updated_role_details.permissions]
        assert "delete:users" in permission_names

    async def test_revoke_permission_from_role(
        self,
        db_session: AsyncSession,
        tenant_id: UUID,
        test_role: RoleModel,
        test_permissions: list[PermissionModel]
    ):
        """Test revoking permissions from role."""
        rbac_service = RBACService(db_session, tenant_id)
        
        # Get initial permission count
        role_details = await rbac_service.get_role_details(test_role.id)
        initial_perm_count = len(role_details.permissions)
        
        # Revoke a permission
        success = await rbac_service.revoke_permission_from_role(
            role_id=test_role.id,
            permission_id=test_permissions[0].id  # read:users
        )
        
        assert success is True
        
        # Verify permission was removed
        updated_role_details = await rbac_service.get_role_details(test_role.id)
        assert len(updated_role_details.permissions) == initial_perm_count - 1
        
        permission_names = [p.name for p in updated_role_details.permissions]
        assert "read:users" not in permission_names

class TestUserRoleAssignment:
    """Test user-role relationship management."""
    
    async def test_assign_role_to_user(
        self,
        db_session: AsyncSession,
        tenant_id: UUID,
        test_user: UserModel,
        test_role: RoleModel,
        admin_user: UserModel
    ):
        """Test assigning role to user."""
        rbac_service = RBACService(db_session, tenant_id)
        
        success = await rbac_service.assign_role_to_user(
            user_id=test_user.id,
            role_id=test_role.id,
            assigned_by=admin_user.id,
            assignment_reason="Test assignment"
        )
        
        assert success is True
        
        # Verify user has the role
        user_roles = await rbac_service.role_repo.get_user_roles(test_user.id)
        role_ids = [r.id for r in user_roles]
        assert test_role.id in role_ids

    async def test_revoke_role_from_user(
        self,
        db_session: AsyncSession,
        tenant_id: UUID,
        test_user: UserModel,
        test_role: RoleModel,
        admin_user: UserModel
    ):
        """Test revoking role from user."""
        rbac_service = RBACService(db_session, tenant_id)
        
        # First assign the role
        await rbac_service.assign_role_to_user(
            user_id=test_user.id,
            role_id=test_role.id,
            assigned_by=admin_user.id
        )
        
        # Verify assignment
        user_roles = await rbac_service.role_repo.get_user_roles(test_user.id)
        assert len(user_roles) > 0
        
        # Revoke the role
        success = await rbac_service.revoke_role_from_user(test_user.id, test_role.id)
        assert success is True
        
        # Verify role was revoked
        user_roles = await rbac_service.role_repo.get_user_roles(test_user.id)
        role_ids = [r.id for r in user_roles]
        assert test_role.id not in role_ids

    async def test_bulk_role_assignment(
        self,
        db_session: AsyncSession,
        tenant_id: UUID,
        admin_user: UserModel,
        test_permissions: list[PermissionModel]
    ):
        """Test bulk role assignment to multiple users."""
        rbac_service = RBACService(db_session, tenant_id)
        user_service = UserService(db_session, tenant_id)
        
        # Create multiple test users
        test_users = []
        for i in range(3):
            user_data = UserCreateSchema(
                username=f"bulkuser{i}",
                email=f"bulk{i}@example.com",
                first_name=f"Bulk{i}",
                last_name="User",
                user_type=UserType.CUSTOMER,
                password="SecurePass123!",
                terms_accepted=True,
                privacy_accepted=True
            )
            user_response = await user_service.create_user(user_data)
            user = await user_service.user_repo.get_by_id(user_response.id)
            test_users.append(user)
        
        # Create multiple test roles
        test_roles = []
        for i in range(2):
            role_data = RoleCreateSchema(
                name=f"bulk_role_{i}",
                display_name=f"Bulk Role {i}",
                description=f"Bulk test role {i}",
                role_category=RoleCategory.CUSTOM,
                permission_ids=[test_permissions[i].id]
            )
            role_response = await rbac_service.create_role(role_data, admin_user.id)
            role = await rbac_service.role_repo.get_by_id(role_response.id)
            test_roles.append(role)
        
        # Perform bulk assignment
        user_ids = [u.id for u in test_users]
        role_ids = [r.id for r in test_roles]
        
        assignments = await rbac_service.bulk_assign_roles(
            user_ids=user_ids,
            role_ids=role_ids,
            assigned_by=admin_user.id,
            assignment_reason="Bulk test assignment"
        )
        
        # Should have 3 users × 2 roles = 6 assignments
        assert len(assignments) == 6
        
        # Verify each user has both roles
        for user in test_users:
            user_roles = await rbac_service.role_repo.get_user_roles(user.id)
            user_role_ids = [r.id for r in user_roles]
            for role in test_roles:
                assert role.id in user_role_ids

class TestPermissionChecking:
    """Test permission checking and authorization."""
    
    async def test_user_permission_check(
        self,
        db_session: AsyncSession,
        tenant_id: UUID,
        test_user: UserModel,
        test_role: RoleModel,
        admin_user: UserModel
    ):
        """Test checking user permissions."""
        rbac_service = RBACService(db_session, tenant_id)
        
        # Assign role to user
        await rbac_service.assign_role_to_user(
            user_id=test_user.id,
            role_id=test_role.id,
            assigned_by=admin_user.id
        )
        
        # Check permission that user should have
        result = await rbac_service.check_user_permission(
            user_id=test_user.id,
            permission_name="read:users"
        )
        
        assert result.has_permission is True
        assert result.user_id == test_user.id
        assert result.permission_name == "read:users"
        assert "customer_user" in result.granted_by_roles
        
        # Check permission that user should not have
        result = await rbac_service.check_user_permission(
            user_id=test_user.id,
            permission_name="delete:users"
        )
        
        assert result.has_permission is False
        assert "does not have the required permission" in result.denied_reason

    async def test_user_permission_summary(
        self,
        db_session: AsyncSession,
        tenant_id: UUID,
        test_user: UserModel,
        test_role: RoleModel,
        admin_user: UserModel
    ):
        """Test getting comprehensive user permission summary."""
        rbac_service = RBACService(db_session, tenant_id)
        
        # Assign role to user
        await rbac_service.assign_role_to_user(
            user_id=test_user.id,
            role_id=test_role.id,
            assigned_by=admin_user.id
        )
        
        # Get permission summary
        summary = await rbac_service.get_user_permission_summary(test_user.id)
        
        assert summary.user_id == test_user.id
        assert len(summary.effective_permissions) > 0
        assert len(summary.roles) > 0
        assert len(summary.permission_details) > 0
        
        # Verify specific permissions
        assert "read:users" in summary.effective_permissions
        assert "write:users" in summary.effective_permissions
        
        # Verify role information
        role_names = [r.name for r in summary.roles]
        assert "customer_user" in role_names

class TestTenantIsolation:
    """Test tenant isolation in RBAC system."""
    
    async def test_role_tenant_isolation(self, db_session: AsyncSession):
        """Test that roles are isolated between tenants."""
        tenant1_id = uuid4()
        tenant2_id = uuid4()
        
        rbac_service1 = RBACService(db_session, tenant1_id)
        rbac_service2 = RBACService(db_session, tenant2_id)
        
        # Create role in tenant 1
        role_data = RoleCreateSchema(
            name="tenant1_role",
            display_name="Tenant 1 Role",
            description="Role for tenant 1",
            role_category=RoleCategory.USER
        )
        
        role1 = await rbac_service1.create_role(role_data)
        
        # Try to access role from tenant 2
        role_from_tenant2 = await rbac_service2.role_repo.get_by_id(role1.id)
        assert role_from_tenant2 is None  # Should not be accessible
        
        # Search should not return cross-tenant roles
        search_params = RoleSearchSchema(query="tenant1", page=1, page_size=10)
        roles, total_count = await rbac_service2.search_roles(search_params)
        
        assert total_count == 0
        assert len(roles) == 0

    async def test_user_role_assignment_tenant_isolation(
        self, 
        db_session: AsyncSession
    ):
        """Test that user-role assignments respect tenant boundaries."""
        tenant1_id = uuid4()
        tenant2_id = uuid4()
        
        user_service1 = UserService(db_session, tenant1_id)
        rbac_service1 = RBACService(db_session, tenant1_id)
        rbac_service2 = RBACService(db_session, tenant2_id)
        
        # Create user in tenant 1
        user_data = UserCreateSchema(
            username="tenant1user",
            email="tenant1@example.com",
            first_name="Tenant1",
            last_name="User",
            user_type=UserType.CUSTOMER,
            password="SecurePass123!",
            terms_accepted=True,
            privacy_accepted=True
        )
        user1_response = await user_service1.create_user(user_data)
        
        # Create role in tenant 1
        role_data = RoleCreateSchema(
            name="tenant1_role",
            display_name="Tenant 1 Role",
            description="Role for tenant 1",
            role_category=RoleCategory.USER
        )
        role1 = await rbac_service1.create_role(role_data)
        
        # Try to assign tenant 1 role to user from tenant 2 service
        with pytest.raises(ValueError):
            await rbac_service2.assign_role_to_user(
                user_id=user1_response.id,
                role_id=role1.id
            )