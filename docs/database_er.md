# ANNADATA AI — Database Architecture & Entity Relationship (ER) Model

## 1. Database Overview
ANNADATA AI uses SQLAlchemy ORM backed by SQLite (for rapid local deployment and academic viva demonstrations) and is fully compatible with enterprise PostgreSQL databases. All migrations are tracked via Alembic (Flask-Migrate) with explicit schema revision histories.

---

## 2. Mermaid Entity-Relationship Diagram

```mermaid
erDiagram
    User ||--o| Restaurant : "operates (1:1)"
    User ||--o| NGO : "manages (1:1)"
    User ||--o| Volunteer : "operates (1:1)"
    User ||--o{ Notification : "receives (1:N)"
    User ||--o{ AuditLog : "initiates (1:N)"

    Restaurant ||--o{ FoodDonation : "donates (1:N)"
    NGO ||--o{ DonationRequest : "receives (1:N)"
    NGO ||--o{ BeneficiaryDemand : "publishes (1:N)"
    NGO ||--o{ RescueMission : "destination_for (1:N)"

    Volunteer ||--o{ PickupAssignment : "assigned_to (1:N)"
    Volunteer ||--o{ RescueMission : "couriers (1:N)"

    FoodDonation ||--o| FoodSafetyAssessment : "evaluated_by (1:1)"
    FoodDonation ||--o{ DonationRequest : "offered_as (1:N)"
    FoodDonation ||--o{ RescueMission : "rescued_via (1:N)"
    FoodDonation ||--o{ AgentExecutionLog : "processed_by (1:N)"

    RescueMission ||--o| ImpactRecord : "generates_upon_delivery (1:1)"
    RescueMission ||--o{ PickupAssignment : "tracked_by (1:N)"

    User {
        int id PK
        string role "restaurant | ngo | volunteer | admin"
        string email UK
        string password_hash
        string full_name
        string phone
        boolean is_active
        datetime created_at
    }

    Restaurant {
        int id PK
        int user_id FK, UK
        string business_name
        string food_type
        string location_address
        float latitude
        float longitude
        datetime created_at
    }

    NGO {
        int id PK
        int user_id FK, UK
        string organization_name
        string registration_number
        string food_preferences
        int capacity_people
        string location_address
        float latitude
        float longitude
        boolean is_active
        datetime created_at
    }

    Volunteer {
        int id PK
        int user_id FK, UK
        boolean available
        float max_distance_km
        float latitude
        float longitude
        string vehicle_type "bike | scooter | car | van"
        datetime created_at
    }

    FoodDonation {
        int id PK
        string rescue_code UK, "ANN-RESCUE-YYYYMMDD-XXXX"
        int restaurant_id FK
        string food_name
        string category
        int quantity
        string unit "kg | packets | trays"
        datetime preparation_time
        datetime expiry_time
        datetime collection_deadline
        string location_address
        float latitude
        float longitude
        string status "pending_analysis | suitable | unsuitable | matched | completed"
        float suitability_score
        text analysis_report
        boolean is_emergency
        string storage_temperature
        string dietary_flags
        string packaging_type
        datetime created_at
    }

    FoodSafetyAssessment {
        int id PK
        int donation_id FK, UK
        boolean visual_inspection_passed
        boolean packaging_intact
        boolean temperature_controlled
        boolean allergens_declared
        boolean hygiene_verified
        float temperature_celsius
        string risk_level "low | medium | high | critical"
        text ai_risk_observations
        int verified_by_user_id FK
        datetime verified_at
        datetime created_at
    }

    DonationRequest {
        int id PK
        int donation_id FK
        int ngo_id FK
        string status "pending | accepted | rejected | expired"
        float distance_km
        float match_score "0 to 100"
        text score_breakdown "JSON explanation"
        datetime responded_at
        datetime created_at
    }

    RescueMission {
        int id PK
        string mission_code UK, "ANN-MSN-YYYYMMDD-XXXX"
        int donation_id FK
        int ngo_id FK
        int volunteer_id FK
        string status "10-stage FSM lifecycle"
        string pickup_pin "4-digit secret"
        string delivery_pin "4-digit secret"
        datetime pickup_time
        datetime delivery_time
        text notes
        text cancellation_reason
        datetime created_at
    }

    ImpactRecord {
        int id PK
        int mission_id FK, UK
        int donation_id FK
        float quantity_kg
        int meals_served
        int beneficiaries_reached
        float co2_saved_kg "2.5 x kg"
        float water_saved_liters "250.0 x kg"
        datetime verified_at
        datetime created_at
    }

    BeneficiaryDemand {
        int id PK
        int ngo_id FK
        string food_category
        int required_servings
        string urgency "routine | elevated | critical"
        string dietary_preference
        text notes
        datetime needed_by
        boolean is_fulfilled
        datetime created_at
    }

    Notification {
        int id PK
        int user_id FK
        string title
        text message
        string category "mission | emergency | match | general"
        boolean is_read
        string link_url
        datetime created_at
    }

    AuditLog {
        int id PK
        int user_id FK
        string action
        string target_type
        int target_id
        text details
        string ip_address
        datetime created_at
    }

    DonationForecast {
        int id PK
        string area_name
        string day_of_week
        float expected_quantity_kg
        float confidence_score
        int historical_sample_size
        boolean is_demo_data
        text recommendations
        datetime created_at
    }

    AgentExecutionLog {
        int id PK
        int donation_id FK
        string agent_name
        string task
        text input_data
        text output_data
        string status "success | failed | pending"
        text error_message
        datetime created_at
    }
```
