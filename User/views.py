from django.db import transaction
from django.utils import timezone
from rest_framework import generics, permissions
from .models import*
from .serializers import *
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.authtoken.models import Token 
from django.shortcuts import get_object_or_404
from collections import Counter
import json
import base64
import numpy as np
from PIL import Image
from io import BytesIO
from django.conf import settings
import base64
import numpy as np
from PIL import Image
from io import BytesIO
from collections import defaultdict
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.conf import settings

from sentinelhub import BBox, CRS

from .models import Farms
from .sentinel import get_sentinel_image
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser


class FarmSatelliteView(APIView):

    def post(self, request):
        farm_id = request.data.get("farm_id")

        if not farm_id:
            return Response({"error": "farm_id is required"}, status=400)

        try:
            farm = Farms.objects.get(id=farm_id)
            print(f"Fetching satellite image for farm: {farm} (ID: {farm.id})")
            # -----------------------------------------
            # 1. Convert string → list (if needed)
            # -----------------------------------------
            coords = farm.bbox
            print(f"Fetching satellite image for farm: {coords}")

            coords = farm.bbox

            # -----------------------------------------
            # FIX: convert string → list
            # -----------------------------------------
            if isinstance(coords, str):
                coords = json.loads(coords)

            print(f"DEBUG coords type: {type(coords)}")
            print(f"DEBUG coords: {coords}")

            # -----------------------------------------
            # NOW SAFE TO LOOP
            # -----------------------------------------
            lats = [c[0] for c in coords]
            lons = [c[1] for c in coords]

            min_lat, max_lat = min(lats), max(lats)
            min_lon, max_lon = min(lons), max(lons)

            bbox_coords = [min_lon, min_lat, max_lon, max_lat]

            print(f"DEBUG bbox_coords: {bbox_coords}")

            
            # -----------------------------------------
            # 3. Fetch satellite image
            # -----------------------------------------
            image, date = get_sentinel_image(
                bbox_coords,
                settings.SENTINEL_HUB["CLIENT_ID"],
                settings.SENTINEL_HUB["CLIENT_SECRET"]
            )

            print(f"[DEBUG] Check saved debug images at: /tmp/sentinel_debug/")
            print(f"[DEBUG] image min={image.min()} max={image.max()} mean={image.mean():.2f}")

            # -----------------------------------------
            # 4. Convert image → base64
            # -----------------------------------------
            img = Image.fromarray(np.uint8(image))
            buffer = BytesIO()
            img.save(buffer, format="PNG")

            image_base64 = base64.b64encode(buffer.getvalue()).decode()

            return Response({
                "farm_id": farm.id,
                "image": image_base64,
                "date": date
            })

        except Farms.DoesNotExist:
            return Response({"error": "Farm not found"}, status=404)

        except Exception as e:
            return Response({"error": str(e)}, status=500)
        

class UpdateSectionNameAPI(APIView):

    def post(self, request):
        serializer = UpdateSectionSerializer(data=request.data)

        if serializer.is_valid():
            cnic = serializer.validated_data['cnic']
            section_name = serializer.validated_data['section_name']

            try:
                user = CustomUser.objects.get(cnic=cnic)
                user.section_name = section_name
                user.save()

                return Response({
                    "message": "Section name updated successfully",
                    "cnic": user.cnic,
                    "section_name": user.section_name
                }, status=status.HTTP_200_OK)

            except CustomUser.DoesNotExist:
                return Response({
                    "error": "User with this CNIC does not exist"
                }, status=status.HTTP_404_NOT_FOUND)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
# Followers APIs
class UserFollwersListCreateView(generics.ListCreateAPIView):
    queryset = UserFollwers.objects.all()
    serializer_class = UserFollwersSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserFollwersRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = UserFollwers.objects.all()
    serializer_class = UserFollwersSerializer
    permission_classes = [permissions.IsAuthenticated]

# Following APIs
class UserFollowingListCreateView(generics.ListCreateAPIView):
    queryset = UserFollwing.objects.all()
    serializer_class = UserFollwingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserFollowingRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = UserFollwing.objects.all()
    serializer_class = UserFollwingSerializer
    permission_classes = [permissions.IsAuthenticated]


class UserProfileView(generics.RetrieveUpdateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated] 
    lookup_field = 'id'
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return CustomUser.objects.filter(id=self.request.user.id)

class LoginAPIView(APIView):
    """
    Login API that authenticates user via CNIC and password
    """
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']

        # Create or get token
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            "message": "Login successful",
            "token": token.key,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "cnic": user.cnic,
                "mobile": user.mobile_number,
                "role": user.role.name
            }
        }, status=status.HTTP_200_OK)
    

# LIST + CREATE
class FarmsListCreateView(generics.ListCreateAPIView):

    serializer_class = FarmsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # show only farms created by logged-in user
        return Farms.objects.filter(created_by=self.request.user).order_by("-id")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# RETRIEVE + UPDATE + DELETE
class FarmsDetailView(generics.RetrieveUpdateDestroyAPIView):

    serializer_class = FarmsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # security: user can access only own farms
        return Farms.objects.filter(created_by=self.request.user)
    

class FarmerListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        farmers = CustomUser.objects.filter(role__name="Farmer")
        serializer = FarmerListSerializer(farmers, many=True)
        return Response(serializer.data)
    
class UserFarmsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        user = get_object_or_404(CustomUser, id=user_id)
        farms = Farms.objects.filter(created_by=user)

        serializer = FarmSerializer(farms, many=True)
        return Response(serializer.data)
    


class SignupAPIView(APIView):

    def post(self, request):
        serializer = SignupSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": "User created successfully",
                "user_id": user.id,
                "username": user.username,
                "mobile_number": user.mobile_number
            }, status=status.HTTP_201_CREATED)

        return Response({
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    


# ---------------- ADD CROP ----------------

class UpsertCropAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        If user already has crops entry with the same ID, update it.
        Otherwise, create a new entry.
        """
        user = request.user
        data = request.data.copy()
        data['user'] = user.id

        crop_id = data.get("id")  # optional: if client sends id for update

        if crop_id:
            # Try to fetch existing crop
            crop = CropDetails.objects.filter(id=crop_id, user=user).first()
            if crop:
                serializer = CropDetailsSerializer(crop, data=data, partial=True)
                action = "updated"
            else:
                serializer = CropDetailsSerializer(data=data)
                action = "added"
        else:
            # No ID sent → check if user has any crops entry
            crop = CropDetails.objects.filter(user=user).first()
            if crop:
                serializer = CropDetailsSerializer(crop, data=data, partial=True)
                action = "updated"
            else:
                serializer = CropDetailsSerializer(data=data)
                action = "added"

        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": f"Crops {action} successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

# ---------------- GET CROPS ----------------

class GetUserFirstCropAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Returns the first crop entry for the current user
        with crop_name as a list.
        """
        user = request.user

        # Get first crop entry
        crop = CropDetails.objects.filter(user=user).first()

        if not crop:
            return Response({"message": "No crops found for this user"}, status=404)

        # Split comma-separated crop names
        crop_list = [c.strip() for c in crop.crop_name.split(",") if c.strip()]

        return Response({
            "id": crop.id,
            "user": crop.user.id,
            "crop_name": crop_list
        })
    
class MostCommonCropsAPIView(APIView):

    def get(self, request):
        crop_entries = CropDetails.objects.values_list("crop_name", flat=True)

        all_crops = []
        for entry in crop_entries:
            crops = [c.strip().lower() for c in entry.split(",") if c.strip()]
            all_crops.extend(crops)

        if not all_crops:
            return Response({"most_common_crops": []})

        crop_count = Counter(all_crops)

        # Get the maximum count
        max_count = max(crop_count.values())

        # Filter only crops that have this maximum count
        most_common = [
            {"crop": crop, "count": count}
            for crop, count in crop_count.items()
            if count == max_count
        ]

        return Response({"most_common_crops": most_common})


class UserDashboardAPIView(APIView):

    def get(self, request):
        users = CustomUser.objects.select_related('role', 'user_creator').all()

        grouped_data = defaultdict(list)
        no_creator_users = []

        for user in users:
            data = {
                "username": user.username,
                "cnic": user.cnic,
                "section_name": user.section_name,
                "role_name": user.role.name if user.role else None,
                "created_at": user.created_at
            }

            if user.user_creator:
                creator_key = f"{user.user_creator.id}-{user.user_creator.username}"
                grouped_data[creator_key].append(data)
            else:
                no_creator_users.append(data)

        # Format response
        response_data = []

        for creator, user_list in grouped_data.items():
            creator_id, creator_name = creator.split('-')

            response_data.append({
                "creator_id": creator_id,
                "creator_name": creator_name,
                "total_users": len(user_list),
                "users": user_list
            })

        return Response({
            "creators": response_data,
            "no_creator": {
                "total_users": len(no_creator_users),
                "users": no_creator_users
            }
        })



# USER STATS API 
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncDate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import CustomUser


class UserStatisticsAPIView(APIView):

    def get(self, request):
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        last_7_days = today - timedelta(days=6)
        last_30_days = today - timedelta(days=29)

        total_users = CustomUser.objects.count()

        users_today = CustomUser.objects.filter(
            created_at__date=today
        ).count()

        users_yesterday = CustomUser.objects.filter(
            created_at__date=yesterday
        ).count()

        def get_users_by_date(start_date):
            daily_data = (
                CustomUser.objects.filter(created_at__date__gte=start_date)
                .annotate(date=TruncDate("created_at"))
                .values("date")
                .annotate(total=Count("id"))
                .order_by("date")
            )

            result = []

            for item in daily_data:
                users = CustomUser.objects.filter(
                    created_at__date=item["date"]
                ).values(
                    "id",
                    "username",
                    "mobile_number",
                    "cnic",
                    "email",
                    "is_active",
                    "is_staff",
                    "created_at",
                    "role__name",
                    "section_name",
                )

                result.append({
                    "date": item["date"],
                    "total": item["total"],
                    "users": list(users)
                })

            return result

        return Response({
            "summary": {
                "total_users": total_users,
                "users_today": users_today,
                "users_yesterday": users_yesterday,
            },
            "last_7_days": get_users_by_date(last_7_days),
            "last_30_days": get_users_by_date(last_30_days),
        }, status=status.HTTP_200_OK)

class DeleteAccountAPIView(APIView):
    """
    Soft account deletion.

    The user row is retained. The account is disabled, marked as deleted,
    and the mobile number is released so the same number can be used to
    register a new account.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if user.is_deleted:
            return Response(
                {
                    "status": "deleted",
                    "message": "This account has already been deleted.",
                },
                status=status.HTTP_200_OK,
            )

        user.deleted_mobile_number = user.mobile_number
        user.mobile_number = None
        user.is_deleted = True
        user.deleted_at = timezone.now()
        user.is_active = False

        user.save(
            update_fields=[
                "deleted_mobile_number",
                "mobile_number",
                "is_deleted",
                "deleted_at",
                "is_active",
            ]
        )

        return Response(
            {
                "status": "deleted",
                "message": "Your account has been deleted.",
            },
            status=status.HTTP_200_OK,
        )


# ==========================================================
# USER BLOCKING
# ==========================================================
class UserBlockListCreateView(APIView):
    """GET -> blocked users list.  POST -> block a user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        blocks = (
            UserBlock.objects.filter(blocker=request.user, is_active=True)
            .select_related("blocked")
            .order_by("-updated_at")
        )
        serializer = BlockedUserSerializer(blocks, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CreateUserBlockSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        target = serializer.context["target_user"]

        with transaction.atomic():
            block, created = UserBlock.objects.get_or_create(
                blocker=request.user,
                blocked=target,
                defaults={"is_active": True},
            )

            already_blocked = not created and block.is_active

            if not already_blocked:
                if not block.is_active:
                    block.is_active = True
                    block.save(update_fields=["is_active", "updated_at"])

                UserBlockLog.objects.create(
                    blocker=request.user,
                    blocked=target,
                    action=UserBlockLog.ACTION_BLOCK,
                )

        return Response(
            {
                "message": "User blocked.",
                "user_id": target.id,
                "already_blocked": already_blocked,
            },
            status=status.HTTP_200_OK,
        )


class UserBlockDeleteView(APIView):
    """DELETE -> unblock a user. The row is deactivated, not removed."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, user_id):
        block = UserBlock.objects.filter(
            blocker=request.user,
            blocked_id=user_id,
            is_active=True,
        ).first()

        if block is None:
            return Response(
                {"detail": "This user is not blocked."},
                status=status.HTTP_404_NOT_FOUND,
            )

        with transaction.atomic():
            block.is_active = False
            block.save(update_fields=["is_active", "updated_at"])

            UserBlockLog.objects.create(
                blocker=request.user,
                blocked_id=user_id,
                action=UserBlockLog.ACTION_UNBLOCK,
            )

        return Response(
            {"message": "User unblocked.", "user_id": user_id},
            status=status.HTTP_200_OK,
        )
