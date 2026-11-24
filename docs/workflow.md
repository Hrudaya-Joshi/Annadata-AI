# ANNADATA AI — Operational Workflows & State Machine Specifications

## 1. 10-Stage Rescue Mission Lifecycle (FSM)

The lifecycle of every accepted food rescue is governed by an immutable finite state machine enforced on the backend. Arbitrary status skipping is rejected with strict validation errors.

```mermaid
stateDiagram-v2
    [*] --> submitted : Restaurant Submits Donation
    submitted --> safety_screening : FoodAnalysisAgent Evaluation
    
    safety_screening --> unsuitable : Fails Safety Checklist / Past 4h Window
    unsuitable --> [*] : Archived & Donor Notified

    safety_screening --> ngo_matching : Passes Safety Screening (Suitable)
    
    ngo_matching --> ngo_accepted : Best Matching NGO Accepts Request
    ngo_matching --> emergency_mode : Approaching Deadline (<2h)
    emergency_mode --> ngo_accepted : Backup NGO Accepts

    ngo_accepted --> volunteer_assigned : Volunteer Claims / Assigned to Mission
    
    volunteer_assigned --> pickup_initiated : Volunteer Departs for Restaurant
    
    pickup_initiated --> food_collected : Handover Confirmed with Pickup PIN
    
    food_collected --> delivery_initiated : Volunteer In Transit to NGO
    
    delivery_initiated --> delivery_confirmed : NGO Verifies Delivery with Delivery PIN
    
    delivery_confirmed --> completed : Automated Impact Record Generated
    completed --> [*] : Tamper-Evident History Sealed
```

---

## 2. End-to-End Rescue Sequence Diagram

The interaction flow across all four roles and platform services:

```mermaid
sequenceDiagram
    autonumber
    actor Restaurant as Food Donor
    participant System as ANNADATA AI Engine
    participant Agents as AI Agent Layer
    actor NGO as Relief NGO
    actor Volunteer as Courier Volunteer
    participant Public as Public QR Verifier

    Restaurant->>System: Submit Surplus (6-Step Wizard + Checklist)
    System->>Agents: FoodAnalysisAgent: Safety Screening
    Agents-->>System: Safety: Suitable, Assign Rescue Code
    System->>Agents: NGOMatchingAgent: Run 100-pt Allocation Engine
    Agents-->>NGO: Send Donation Request (Score, Transit Time, Breakdown)
    
    NGO->>System: Accept Donation Request
    System->>System: Provision RescueMission (State: ngo_accepted, PINs Generated)
    System->>Volunteer: Broadcast Mission to Nearby Active Volunteers
    
    Volunteer->>System: Claim Assignment (State: volunteer_assigned)
    Volunteer->>System: Mark "En Route to Kitchen" (State: pickup_initiated)
    
    Volunteer->>Restaurant: Arrive at Kitchen, Inspect Packaging
    Restaurant->>Volunteer: Disclose 4-digit Pickup PIN
    Volunteer->>System: Enter Pickup PIN & Confirm Rescued
    System->>System: Verify PIN -> Transition to food_collected
    
    Volunteer->>System: Depart for NGO (State: delivery_initiated)
    Volunteer->>NGO: Arrive at Shelter, Hand Over Food
    NGO->>System: Verify Delivery PIN & Actual Weight
    System->>System: Verify PIN -> Transition to completed
    System->>System: Generate Verified ImpactRecord (kg, meals, CO2, water)
    
    Public->>System: Scan QR on Packaging (GET /passport/{code})
    System-->>Public: Tamper-Evident Provenance (Public-Safe, Masked Contacts)
```

---

## 3. Handover PIN Security Protocol

To prevent phantom collections, incorrect drop-offs, or malicious confirmation:
1. **Pickup Verification PIN (`pickup_pin`):**
   - Automatically generated as a cryptographic 4-digit code.
   - Displayed *only* to the Restaurant donor on their donation details dashboard.
   - The courier volunteer must obtain the code from the kitchen manager at physical handover and submit it via `/missions/<id>/handover`.
2. **Delivery Verification PIN (`delivery_pin`):**
   - A separate cryptographic 4-digit code generated upon mission creation.
   - Displayed *only* to the receiving NGO contact person on their mission management page.
   - Entered upon physical delivery to verify quantity, condition, and beneficiary reception.

---

## 4. Emergency Rescue Escalation Mode

When a perishable donation's collection deadline drops below the **2-hour critical threshold** without an accepted mission:
1. The background emergency scanner flags the donation (`is_emergency = True`).
2. Immediate push notifications and visual amber/red banners are displayed across all active NGOs within a 15 km radius.
3. The allocation engine identifies up to 3 alternative nearby relief shelters with matching category capacity.
4. Active volunteers receive an expedited dispatch alert to prioritize pickup before spoilage.
