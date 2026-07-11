class ReportCalculator:
    @staticmethod
    def get_summary(student, term):
        # Fetch results for the specific term
        results = student.results.filter(term=term)
        subject_count = results.count()

        # Grade X logic: In Uganda, Grade X usually denotes missing required subjects
        # Minimum subjects for a full result is typically 8
        if subject_count < 8:
            return {
                "aggregates": "N/A", 
                "division": "Grade X", 
                "incomplete": True,
                "count": subject_count
            }

        # Safely extract grade points
        # Using getattr as a fallback in case a record somehow missed the save() logic
        points_list = sorted([getattr(r, 'grade_point', 9) for r in results])
        
        # Calculate Aggregates (Sum of Best 8 grade points)
        best_8_sum = sum(points_list[:8])

        # Division Mapping (Standard O-Level thresholds)
        # Note: Div 1 typically ends at 32 points, Div 2 at 45, etc.
        if 8 <= best_8_sum <= 32:
            division = "Division 1"
        elif 33 <= best_8_sum <= 45:
            division = "Division 2"
        elif 46 <= best_8_sum <= 58:
            division = "Division 3"
        elif 59 <= best_8_sum <= 72:
            division = "Division 4"
        else:
            division = "Division U" # Ungraded/Fail
            
        return {
            "aggregates": best_8_sum, 
            "division": division, 
            "incomplete": False,
            "count": subject_count
        }