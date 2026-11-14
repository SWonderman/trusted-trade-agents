from enum import StrEnum
from typing import Any

from fastapi import HTTPException, status
from pydantic import Field, create_model

from saint_elmo_backend.core.schema import CamelBaseModel

type Headers = dict[str, str]


class ErrorCode(StrEnum):
    # Generic / framework
    INTERNAL = "INTERNAL"
    HTTP_ERROR = "HTTP_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"

    # Auth and tenancy
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    NO_ORGANIZATION = "NO_ORGANIZATION"
    MEMBERSHIP_NOT_FOUND = "MEMBERSHIP_NOT_FOUND"
    ORGANIZATION_INACTIVE = "ORGANIZATION_INACTIVE"
    ORGANIZATION_NOT_FOUND = "ORGANIZATION_NOT_FOUND"
    NOT_ORGANIZATION_OWNER = "NOT_ORGANIZATION_OWNER"
    ORGANIZATION_PROFILE_NOT_FOUND = "ORGANIZATION_PROFILE_NOT_FOUND"
    EMAIL_ALREADY_REGISTERED = "EMAIL_ALREADY_REGISTERED"
    EMAIL_ALREADY_MEMBER = "EMAIL_ALREADY_MEMBER"
    EMAIL_NOT_VERIFIED = "EMAIL_NOT_VERIFIED"
    EMAIL_ALREADY_VERIFIED = "EMAIL_ALREADY_VERIFIED"
    EMAIL_VERIFICATION_NOT_FOUND = "EMAIL_VERIFICATION_NOT_FOUND"
    EMAIL_VERIFICATION_INVALID = "EMAIL_VERIFICATION_INVALID"
    OWNER_ROLE_FORBIDDEN = "OWNER_ROLE_FORBIDDEN"
    ORGANIZATION_LIMIT_REACHED = "ORGANIZATION_LIMIT_REACHED"

    # Invitations
    INVITATION_NOT_FOUND = "INVITATION_NOT_FOUND"
    INVITATION_INVALID = "INVITATION_INVALID"
    INCOMPLETE_REGISTRATION = "INCOMPLETE_REGISTRATION"
    INVITATION_REQUIRES_AUTHENTICATION = "INVITATION_REQUIRES_AUTHENTICATION"
    INVITATION_ACCOUNT_MISMATCH = "INVITATION_ACCOUNT_MISMATCH"

    # Channels / marketplaces
    STOREFRONT_NOT_FOUND = "STOREFRONT_NOT_FOUND"
    STOREFRONT_NOT_SYNCABLE = "STOREFRONT_NOT_SYNCABLE"
    DUPLICATE_STOREFRONT = "DUPLICATE_STOREFRONT"
    MARKETPLACE_MISCONFIGURED = "MARKETPLACE_MISCONFIGURED"
    MARKETPLACE_ACCOUNT_NOT_FOUND = "MARKETPLACE_ACCOUNT_NOT_FOUND"
    INTEGRATION_NOT_FOUND = "INTEGRATION_NOT_FOUND"
    DUPLICATE_MARKETPLACE_ACCOUNT = "DUPLICATE_MARKETPLACE_ACCOUNT"

    # Geo / documents
    COUNTRY_NOT_FOUND = "COUNTRY_NOT_FOUND"
    DOCUMENT_TEMPLATE_NOT_FOUND = "DOCUMENT_TEMPLATE_NOT_FOUND"
    PDF_GENERATION_ERROR = "PDF_GENERATION_ERROR"

    # Events
    EVENT_NOT_FOUND = "EVENT_NOT_FOUND"

    # Orders
    ORDER_NOT_FOUND = "ORDER_NOT_FOUND"
    ORDER_ALREADY_FULFILLED = "ORDER_ALREADY_FULFILLED"
    SHIPPING_ADDRESS_MISSING = "SHIPPING_ADDRESS_MISSING"

    # Shipping / carriers
    CARRIER_REJECTED = "CARRIER_REJECTED"
    CARRIER_UNAVAILABLE = "CARRIER_UNAVAILABLE"
    NO_DEFAULT_CARRIER = "NO_DEFAULT_CARRIER"
    NO_ORIGIN_LOCATION = "NO_ORIGIN_LOCATION"
    CARRIER_SERVICE_NOT_FOUND = "CARRIER_SERVICE_NOT_FOUND"
    CARRIER_ASSIGNMENT_NOT_FOUND = "CARRIER_ASSIGNMENT_NOT_FOUND"

    # Catalog
    BRAND_NOT_FOUND = "BRAND_NOT_FOUND"
    CATEGORY_NOT_FOUND = "CATEGORY_NOT_FOUND"
    PRODUCT_NOT_FOUND = "PRODUCT_NOT_FOUND"
    VARIANT_NOT_FOUND = "VARIANT_NOT_FOUND"
    IDENTIFIER_NOT_FOUND = "IDENTIFIER_NOT_FOUND"
    DUPLICATE_BRAND = "DUPLICATE_BRAND"
    DUPLICATE_CATEGORY = "DUPLICATE_CATEGORY"
    DUPLICATE_SKU = "DUPLICATE_SKU"
    DUPLICATE_IDENTIFIER = "DUPLICATE_IDENTIFIER"

    # Inventory
    LOCATION_NOT_FOUND = "LOCATION_NOT_FOUND"
    DUPLICATE_LOCATION = "DUPLICATE_LOCATION"


class SaintElmoHTTPException(HTTPException):
    def __init__(
        self,
        status_code: int,
        error_code: ErrorCode,
        detail: str,
        headers: Headers | None = None,
    ) -> None:
        self.error_code: ErrorCode = error_code

        super().__init__(
            status_code=status_code,
            detail=detail,
            headers=headers,
        )


class SomethingWentWrong(SaintElmoHTTPException):
    def __init__(self, detail: str = "Something went wrong", headers: Headers | None = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL,
            detail=detail,
            headers=headers,
        )


class InvalidCredentials(SaintElmoHTTPException):
    def __init__(
        self,
        detail: str = "Could not validate credentials",
        headers: Headers | None = None,
    ):
        if headers is None:
            headers = {"WWW-Authenticate": "Bearer"}

        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.INVALID_CREDENTIALS,
            detail=detail,
            headers=headers,
        )


class PermissionDenied(SaintElmoHTTPException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.PERMISSION_DENIED,
            detail=detail,
        )


class NoOrganization(SaintElmoHTTPException):
    def __init__(self, detail: str = "User is not a member of any organization"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.NO_ORGANIZATION,
            detail=detail,
        )


class MembershipNotFound(SaintElmoHTTPException):
    def __init__(self, detail: str = "Membership not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.MEMBERSHIP_NOT_FOUND,
            detail=detail,
        )


class OrganizationInactive(SaintElmoHTTPException):
    def __init__(self, detail: str = "Organization is not active"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.ORGANIZATION_INACTIVE,
            detail=detail,
        )


class EmailAlreadyRegistered(SaintElmoHTTPException):
    def __init__(self, detail: str = "Email is already registered"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code=ErrorCode.EMAIL_ALREADY_REGISTERED,
            detail=detail,
        )


class EmailAlreadyMember(SaintElmoHTTPException):
    def __init__(self, detail: str = "Email is already a member of the organization"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code=ErrorCode.EMAIL_ALREADY_MEMBER,
            detail=detail,
        )


class EmailNotVerified(SaintElmoHTTPException):
    def __init__(
        self,
        detail: str = "Confirm your email address to perform this action",
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.EMAIL_NOT_VERIFIED,
            detail=detail,
        )


class EmailAlreadyVerified(SaintElmoHTTPException):
    def __init__(self, detail: str = "This email address is already confirmed"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code=ErrorCode.EMAIL_ALREADY_VERIFIED,
            detail=detail,
        )


class EmailVerificationNotFound(SaintElmoHTTPException):
    def __init__(self, detail: str = "Email verification not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.EMAIL_VERIFICATION_NOT_FOUND,
            detail=detail,
        )


class EmailVerificationInvalid(SaintElmoHTTPException):
    def __init__(self, detail: str = "This confirmation link has expired. Request a new one."):
        super().__init__(
            status_code=status.HTTP_410_GONE,
            error_code=ErrorCode.EMAIL_VERIFICATION_INVALID,
            detail=detail,
        )


class InvitationNotFound(SaintElmoHTTPException):
    def __init__(self, detail: str = "Invitation not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.INVITATION_NOT_FOUND,
            detail=detail,
        )


class InvitationInvalid(SaintElmoHTTPException):
    def __init__(self, detail: str = "Invitation has expired or was already accepted"):
        super().__init__(
            status_code=status.HTTP_410_GONE,
            error_code=ErrorCode.INVITATION_INVALID,
            detail=detail,
        )


class IncompleteRegistration(SaintElmoHTTPException):
    def __init__(self, detail: str = "First name, last name, and password are required"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.INCOMPLETE_REGISTRATION,
            detail=detail,
        )


class InvitationRequiresAuthentication(SaintElmoHTTPException):
    def __init__(self, detail: str = "Log in as the invited email to accept this invitation"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.INVITATION_REQUIRES_AUTHENTICATION,
            detail=detail,
        )


class InvitationAccountMismatch(SaintElmoHTTPException):
    def __init__(self, detail: str = "This invitation was sent to a different account"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.INVITATION_ACCOUNT_MISMATCH,
            detail=detail,
        )


class OwnerRoleForbidden(SaintElmoHTTPException):
    def __init__(
        self,
        detail: str = "The organization owner's role cannot be changed or assigned",
    ):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code=ErrorCode.OWNER_ROLE_FORBIDDEN,
            detail=detail,
        )


class OrganizationNotFound(SaintElmoHTTPException):
    def __init__(self, detail: str = "Organization not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.ORGANIZATION_NOT_FOUND,
            detail=detail,
        )


class OrganizationLimitReached(SaintElmoHTTPException):
    def __init__(
        self,
        detail: str = "You have reached the maximum number of organizations you can own",
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.ORGANIZATION_LIMIT_REACHED,
            detail=detail,
        )


class NotOrganizationOwner(SaintElmoHTTPException):
    def __init__(self, detail: str = "Only the organization owner can perform this action"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.NOT_ORGANIZATION_OWNER,
            detail=detail,
        )


class StorefrontNotFound(SaintElmoHTTPException):
    def __init__(self, detail: str = "Storefront not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.STOREFRONT_NOT_FOUND,
            detail=detail,
        )


class StorefrontNotSyncable(SaintElmoHTTPException):
    def __init__(self, detail: str = "Storefront is disabled"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code=ErrorCode.STOREFRONT_NOT_SYNCABLE,
            detail=detail,
        )


class MarketplaceMisconfigured(SaintElmoHTTPException):
    def __init__(self, detail: str = "Storefront marketplace connection is misconfigured"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.MARKETPLACE_MISCONFIGURED,
            detail=detail,
        )


class MarketplaceAccountNotFound(SaintElmoHTTPException):
    def __init__(self, detail: str = "Marketplace account not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.MARKETPLACE_ACCOUNT_NOT_FOUND,
            detail=detail,
        )


class IntegrationNotFound(SaintElmoHTTPException):
    def __init__(self, detail: str = "Marketplace integration not found"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.INTEGRATION_NOT_FOUND,
            detail=detail,
        )


class DuplicateMarketplaceAccount(SaintElmoHTTPException):
    def __init__(
        self,
        detail: str = "A marketplace account with this name already exists for this integration",
    ):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code=ErrorCode.DUPLICATE_MARKETPLACE_ACCOUNT,
            detail=detail,
        )


class CountryNotFound(SaintElmoHTTPException):
    def __init__(self, detail: str = "Unknown country iso code"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.COUNTRY_NOT_FOUND,
            detail=detail,
        )


class OrganizationProfileNotFound(SaintElmoHTTPException):
    def __init__(self, detail: str = "Organization profile not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.ORGANIZATION_PROFILE_NOT_FOUND,
            detail=detail,
        )


class DocumentTemplateNotFound(SaintElmoHTTPException):
    def __init__(self, detail: str = "Document template not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.DOCUMENT_TEMPLATE_NOT_FOUND,
            detail=detail,
        )


class DuplicateStorefront(SaintElmoHTTPException):
    def __init__(
        self,
        detail: str = "A storefront with this name already exists for this account",
    ):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code=ErrorCode.DUPLICATE_STOREFRONT,
            detail=detail,
        )


class EventNotFound(SaintElmoHTTPException):
    def __init__(self, detail: str = "Event not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.EVENT_NOT_FOUND,
            detail=detail,
        )


class OrderNotFound(SaintElmoHTTPException):
    def __init__(self, detail: str = "Order not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.ORDER_NOT_FOUND,
            detail=detail,
        )


class OrderAlreadyFulfilled(SaintElmoHTTPException):
    def __init__(self, detail: str = "Order is already fulfilled"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code=ErrorCode.ORDER_ALREADY_FULFILLED,
            detail=detail,
        )


class ShippingAddressMissing(SaintElmoHTTPException):
    def __init__(self, detail: str = "Order has no shipping address"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.SHIPPING_ADDRESS_MISSING,
            detail=detail,
        )


class PdfGenerationFailure(SaintElmoHTTPException):
    def __init__(self, detail: str = "Could not generate a PDF"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.PDF_GENERATION_ERROR,
            detail=detail,
        )


class CarrierRejected(SaintElmoHTTPException):
    def __init__(self, detail: str = "Carrier rejected the shipment"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.CARRIER_REJECTED,
            detail=detail,
        )


class CarrierUnavailable(SaintElmoHTTPException):
    def __init__(self, detail: str = "Carrier is temporarily unavailable"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code=ErrorCode.CARRIER_UNAVAILABLE,
            detail=detail,
        )


class NoDefaultCarrier(SaintElmoHTTPException):
    def __init__(self, detail: str = "No default carrier configured for this storefront"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.NO_DEFAULT_CARRIER,
            detail=detail,
        )


class NoOriginLocation(SaintElmoHTTPException):
    def __init__(self, detail: str = "No active location with an address to ship from"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.NO_ORIGIN_LOCATION,
            detail=detail,
        )


class CarrierServiceNotFound(SaintElmoHTTPException):
    def __init__(self, detail: str = "Carrier service not found"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.CARRIER_SERVICE_NOT_FOUND,
            detail=detail,
        )


class CarrierAssignmentNotFound(SaintElmoHTTPException):
    def __init__(self, detail: str = "Carrier assignment not found for this storefront"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.CARRIER_ASSIGNMENT_NOT_FOUND,
            detail=detail,
        )


class BrandNotFound(SaintElmoHTTPException):
    def __init__(self, detail: str = "Brand not found"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.BRAND_NOT_FOUND,
            detail=detail,
        )


class CategoryNotFound(SaintElmoHTTPException):
    def __init__(self, detail: str = "Category not found"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.CATEGORY_NOT_FOUND,
            detail=detail,
        )


class ProductNotFound(SaintElmoHTTPException):
    def __init__(self, detail: str = "Product not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.PRODUCT_NOT_FOUND,
            detail=detail,
        )


class VariantNotFound(SaintElmoHTTPException):
    def __init__(self, detail: str = "Variant not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.VARIANT_NOT_FOUND,
            detail=detail,
        )


class IdentifierNotFound(SaintElmoHTTPException):
    def __init__(self, detail: str = "Identifier not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.IDENTIFIER_NOT_FOUND,
            detail=detail,
        )


class DuplicateBrand(SaintElmoHTTPException):
    def __init__(self, detail: str = "A brand with this name already exists"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code=ErrorCode.DUPLICATE_BRAND,
            detail=detail,
        )


class DuplicateCategory(SaintElmoHTTPException):
    def __init__(self, detail: str = "A category with this name already exists"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code=ErrorCode.DUPLICATE_CATEGORY,
            detail=detail,
        )


class DuplicateSku(SaintElmoHTTPException):
    def __init__(self, detail: str = "A variant with this SKU already exists"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code=ErrorCode.DUPLICATE_SKU,
            detail=detail,
        )


class DuplicateIdentifier(SaintElmoHTTPException):
    def __init__(self, detail: str = "This identifier already exists"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code=ErrorCode.DUPLICATE_IDENTIFIER,
            detail=detail,
        )


class LocationNotFound(SaintElmoHTTPException):
    def __init__(self, detail: str = "Location not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.LOCATION_NOT_FOUND,
            detail=detail,
        )


class DuplicateLocation(SaintElmoHTTPException):
    def __init__(self, detail: str = "A location with this code already exists"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code=ErrorCode.DUPLICATE_LOCATION,
            detail=detail,
        )


class SaintElmoErrorResponse(CamelBaseModel):
    detail: str
    error_code: ErrorCode


def to_response_error(
    *exceptions: type[SaintElmoHTTPException],
) -> dict[int | str, dict[str, Any]]:
    result: dict[int | str, dict[str, Any]] = {}

    for exc in exceptions:
        instance: SaintElmoHTTPException = exc()  # type: ignore[call-arg]

        SpecificError = create_model(
            f"{exc.__name__}Response",
            __base__=SaintElmoErrorResponse,
            error_code=(ErrorCode, Field(instance.error_code, frozen=True)),
            detail=(str, Field(instance.detail, examples=[instance.detail])),
        )

        entry = result.setdefault(
            instance.status_code,
            {
                "model": SpecificError,
                "description": instance.detail,
                "content": {"application/json": {"examples": {}}},
            },
        )

        example = entry["content"]["application/json"]["examples"]
        example[exc.__name__] = {
            "summary": exc.__name__,
            "value": {
                "detail": instance.detail,
                "error_code": instance.error_code,
            },
        }

    return result
