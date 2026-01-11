"""
Tests for the High School Management System FastAPI application
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        activity_name: {
            "description": activity["description"],
            "schedule": activity["schedule"],
            "max_participants": activity["max_participants"],
            "participants": activity["participants"].copy()
        }
        for activity_name, activity in activities.items()
    }
    
    yield
    
    # Restore original state
    for activity_name, activity_data in original_activities.items():
        activities[activity_name]["participants"] = activity_data["participants"].copy()


class TestRoot:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static_index(self, client):
        """Test that root redirects to the static index page"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_200(self, client):
        """Test that GET /activities returns 200 status code"""
        response = client.get("/activities")
        assert response.status_code == 200
    
    def test_get_activities_returns_dict(self, client):
        """Test that GET /activities returns a dictionary"""
        response = client.get("/activities")
        assert isinstance(response.json(), dict)
    
    def test_get_activities_contains_expected_activities(self, client):
        """Test that GET /activities contains expected activity names"""
        response = client.get("/activities")
        data = response.json()
        
        expected_activities = [
            "Chess Club",
            "Programming Class",
            "Gym Class",
            "Soccer Team",
            "Swimming Club",
            "Art Studio",
            "Drama Club",
            "Debate Team",
            "Science Olympiad"
        ]
        
        for activity in expected_activities:
            assert activity in data
    
    def test_activity_structure(self, client):
        """Test that each activity has the expected structure"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity in data.items():
            assert "description" in activity
            assert "schedule" in activity
            assert "max_participants" in activity
            assert "participants" in activity
            assert isinstance(activity["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_for_existing_activity(self, client):
        """Test successful signup for an existing activity"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        assert "Signed up newstudent@mergington.edu for Chess Club" in response.json()["message"]
    
    def test_signup_adds_participant_to_activity(self, client):
        """Test that signup actually adds the participant to the activity"""
        email = "test@mergington.edu"
        client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        
        # Verify participant was added
        response = client.get("/activities")
        data = response.json()
        assert email in data["Chess Club"]["participants"]
    
    def test_signup_for_nonexistent_activity(self, client):
        """Test signup for a non-existent activity returns 404"""
        response = client.post(
            "/activities/Fake Club/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"
    
    def test_duplicate_signup(self, client):
        """Test that duplicate signup returns 400"""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        
        # Second signup should fail
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Student already signed up for this activity"
    
    def test_signup_with_existing_participant(self, client):
        """Test that signing up with an already registered email fails"""
        # Try to sign up with an email that's already in the initial data
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "michael@mergington.edu"}
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Student already signed up for this activity"


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_from_activity(self, client):
        """Test successful unregistration from an activity"""
        # First, sign up a student
        email = "unregister@mergington.edu"
        client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        
        # Then unregister
        response = client.delete(
            "/activities/Chess Club/unregister",
            params={"email": email}
        )
        assert response.status_code == 200
        assert f"Unregistered {email} from Chess Club" in response.json()["message"]
    
    def test_unregister_removes_participant(self, client):
        """Test that unregister actually removes the participant"""
        email = "remove@mergington.edu"
        
        # Sign up
        client.post(
            "/activities/Programming Class/signup",
            params={"email": email}
        )
        
        # Verify participant was added
        response = client.get("/activities")
        assert email in response.json()["Programming Class"]["participants"]
        
        # Unregister
        client.delete(
            "/activities/Programming Class/unregister",
            params={"email": email}
        )
        
        # Verify participant was removed
        response = client.get("/activities")
        assert email not in response.json()["Programming Class"]["participants"]
    
    def test_unregister_from_nonexistent_activity(self, client):
        """Test unregister from non-existent activity returns 404"""
        response = client.delete(
            "/activities/Fake Club/unregister",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"
    
    def test_unregister_not_signed_up(self, client):
        """Test unregister when student is not signed up returns 400"""
        response = client.delete(
            "/activities/Chess Club/unregister",
            params={"email": "notsignedup@mergington.edu"}
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Student is not signed up for this activity"
    
    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant from initial data"""
        # Michael is already signed up for Chess Club in the initial data
        email = "michael@mergington.edu"
        
        response = client.delete(
            "/activities/Chess Club/unregister",
            params={"email": email}
        )
        assert response.status_code == 200
        
        # Verify he was removed
        response = client.get("/activities")
        assert email not in response.json()["Chess Club"]["participants"]


class TestIntegration:
    """Integration tests for multiple operations"""
    
    def test_signup_and_unregister_flow(self, client):
        """Test complete flow of signup and unregister"""
        email = "flow@mergington.edu"
        activity = "Drama Club"
        
        # Get initial participant count
        response = client.get("/activities")
        initial_count = len(response.json()[activity]["participants"])
        
        # Sign up
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response.status_code == 200
        
        # Verify count increased
        response = client.get("/activities")
        assert len(response.json()[activity]["participants"]) == initial_count + 1
        
        # Unregister
        response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        assert response.status_code == 200
        
        # Verify count back to initial
        response = client.get("/activities")
        assert len(response.json()[activity]["participants"]) == initial_count
    
    def test_multiple_activities_signup(self, client):
        """Test signing up for multiple different activities"""
        email = "multi@mergington.edu"
        activities_list = ["Chess Club", "Programming Class", "Art Studio"]
        
        for activity in activities_list:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify student is in all activities
        response = client.get("/activities")
        data = response.json()
        for activity in activities_list:
            assert email in data[activity]["participants"]
