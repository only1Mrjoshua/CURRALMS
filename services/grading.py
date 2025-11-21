from schemas.quiz import QuestionTypeEnum
from typing import Dict, Any, List

class GradingService:
    
    @staticmethod
    def grade_multiple_choice(user_answer: str, correct_answer: str) -> bool:
        return user_answer.strip().lower() == correct_answer.strip().lower()
    
    @staticmethod
    def grade_true_false(user_answer: str, correct_answer: str) -> bool:
        return str(user_answer).lower() == str(correct_answer).lower()
    
    @staticmethod
    def grade_coding_question(user_code: str, test_cases: List[Dict]) -> Dict[str, Any]:
        """
        Grade coding questions using test cases
        For now, using simple string comparison
        """
        try:
            passed_tests = 0
            total_tests = len(test_cases)
            test_details = []
            
            for test_case in test_cases:
                expected_output = test_case.get('expected_output', '')
                # Simple check - in production, use Judge0 or similar
                passed = expected_output.lower() in user_code.lower()
                
                if passed:
                    passed_tests += 1
                
                test_details.append({
                    'test_case': test_case.get('input', ''),
                    'expected': expected_output,
                    'passed': passed
                })
            
            return {
                'passed': passed_tests == total_tests,
                'score': (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
                'passed_tests': passed_tests,
                'total_tests': total_tests,
                'details': test_details
            }
            
        except Exception as e:
            return {
                'passed': False,
                'score': 0,
                'error': str(e),
                'details': []
            }
    
    def grade_question(self, question_type: str, user_answer: str, correct_answer: str, 
                      test_cases: List[Dict] = None) -> Dict[str, Any]:
        
        if question_type == QuestionTypeEnum.multiple_choice:
            correct = self.grade_multiple_choice(user_answer, correct_answer)
            return {'correct': correct, 'details': None}
        
        elif question_type == QuestionTypeEnum.true_false:
            correct = self.grade_true_false(user_answer, correct_answer)
            return {'correct': correct, 'details': None}
        
        elif question_type == QuestionTypeEnum.coding:
            return self.grade_coding_question(user_answer, test_cases or [])
        
        else:
            return {'correct': False, 'details': 'Unknown question type'}