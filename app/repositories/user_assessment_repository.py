"""Repositorio de intentos de evaluación y progreso."""

from collections.abc import Sequence
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment_option import AssessmentOption
from app.models.assessment_question import AssessmentQuestion
from app.models.course import Course
from app.models.module import Module
from app.models.module_assessment import ModuleAssessment
from app.models.user_assessment_attempt import (
    UserAssessmentAnswer,
    UserAssessmentAttempt,
)
from app.schemas.module_assessment import (
    AnswerResult,
    AttemptResult,
    CourseProgressSummary,
    ModuleProgressItem,
)


class UserAssessmentRepository:
    async def create_attempt(
        self,
        db: AsyncSession,
        *,
        assessment_id: int,
        user_id: int,
    ) -> UserAssessmentAttempt:
        attempt = UserAssessmentAttempt(
            assessment_id=assessment_id,
            user_id=user_id,
            started_at=datetime.now(timezone.utc),
        )
        db.add(attempt)
        await db.flush()
        await db.refresh(attempt)
        return attempt

    async def submit_answers(
        self,
        db: AsyncSession,
        attempt: UserAssessmentAttempt,
        answers: list[dict],
    ) -> AttemptResult:
        assessment = await db.execute(
            select(ModuleAssessment)
            .where(ModuleAssessment.id == attempt.assessment_id)
            .options(
                selectinload(ModuleAssessment.questions).selectinload(
                    AssessmentQuestion.options
                )
            )
        )
        assessment = assessment.scalar_one_or_none()
        if not assessment:
            raise ValueError("Assessment no encontrado")

        questions_map = {q.id: q for q in assessment.questions}
        options_map: dict[int, AssessmentOption] = {}
        for q in assessment.questions:
            for opt in q.options:
                options_map[opt.id] = opt

        total_points = sum(q.points for q in assessment.questions)
        earned_points = 0
        answer_results: list[AnswerResult] = []

        for ans in answers:
            qid = ans["question_id"]
            optid = ans["selected_option_id"]

            question = questions_map.get(qid)
            if not question:
                raise ValueError(f"Pregunta {qid} no encontrada")

            option = options_map.get(optid)
            if not option or option.question_id != qid:
                raise ValueError(
                    f"Opción {optid} no válida para pregunta {qid}"
                )

            is_correct = option.is_correct
            if is_correct:
                earned_points += question.points

            answer_obj = UserAssessmentAnswer(
                attempt_id=attempt.id,
                question_id=qid,
                selected_option_id=optid,
                is_correct=is_correct,
            )
            db.add(answer_obj)

            correct_opt = next(
                (o for o in question.options if o.is_correct), None
            )

            answer_results.append(
                AnswerResult(
                    question_id=qid,
                    question_text=question.question_text,
                    selected_option_id=optid,
                    is_correct=is_correct,
                    correct_option_id=correct_opt.id if correct_opt else None,
                )
            )

        score = (
            Decimal(0)
            if total_points == 0
            else Decimal(str(round((earned_points / total_points) * 100, 2)))
        )
        passed = score >= Decimal(str(assessment.passing_score))

        attempt.score = score
        attempt.passed = passed
        attempt.finished_at = datetime.now(timezone.utc)

        await db.flush()
        await db.refresh(attempt)

        return AttemptResult(
            attempt_id=attempt.id,
            score=float(score),
            passed=passed,
            total_points=total_points,
            earned_points=earned_points,
            answers=answer_results,
        )

    async def get_attempt(
        self, db: AsyncSession, attempt_id: int
    ) -> UserAssessmentAttempt | None:
        r = await db.execute(
            select(UserAssessmentAttempt)
            .where(UserAssessmentAttempt.id == attempt_id)
            .options(
                selectinload(UserAssessmentAttempt.answers).selectinload(
                    UserAssessmentAnswer.question
                )
            )
        )
        return r.scalar_one_or_none()

    async def get_attempts_by_assessment(
        self,
        db: AsyncSession,
        assessment_id: int,
        user_id: int,
    ) -> Sequence[UserAssessmentAttempt]:
        r = await db.execute(
            select(UserAssessmentAttempt)
            .where(
                UserAssessmentAttempt.assessment_id == assessment_id,
                UserAssessmentAttempt.user_id == user_id,
            )
            .order_by(UserAssessmentAttempt.started_at.desc())
        )
        return r.scalars().all()

    async def has_passed(
        self,
        db: AsyncSession,
        assessment_id: int,
        user_id: int,
    ) -> bool:
        r = await db.execute(
            select(UserAssessmentAttempt).where(
                UserAssessmentAttempt.assessment_id == assessment_id,
                UserAssessmentAttempt.user_id == user_id,
                UserAssessmentAttempt.passed == True,
            )
        )
        return r.scalar_one_or_none() is not None

    async def get_course_progress(
        self,
        db: AsyncSession,
        user_id: int,
        course_id: int,
    ) -> CourseProgressSummary:
        course_r = await db.execute(
            select(Course).where(Course.id == course_id)
        )
        course = course_r.scalar_one_or_none()
        if not course:
            raise ValueError("Curso no encontrado")

        modules_r = await db.execute(
            select(Module)
            .where(Module.course_id == course_id)
            .order_by(Module.order_index)
        )
        modules = modules_r.scalars().all()

        module_items: list[ModuleProgressItem] = []
        completed = 0

        for mod in modules:
            assessment_r = await db.execute(
                select(ModuleAssessment).where(
                    ModuleAssessment.module_id == mod.id
                )
            )
            assessment = assessment_r.scalar_one_or_none()

            if not assessment:
                module_items.append(
                    ModuleProgressItem(
                        module_id=mod.id,
                        module_title=mod.title,
                        module_order=mod.order_index,
                        total_assessment_questions=0,
                        attempts_count=0,
                        last_score=None,
                        passed=False,
                    )
                )
                continue

            questions_r = await db.execute(
                select(func.count(AssessmentQuestion.id)).where(
                    AssessmentQuestion.assessment_id == assessment.id
                )
            )
            total_q = questions_r.scalar() or 0

            attempts_r = await db.execute(
                select(UserAssessmentAttempt).where(
                    UserAssessmentAttempt.assessment_id == assessment.id,
                    UserAssessmentAttempt.user_id == user_id,
                )
                .order_by(UserAssessmentAttempt.finished_at.desc().nullslast())
            )
            attempts = attempts_r.scalars().all()

            attempts_count = len(attempts)
            last_score = float(attempts[0].score) if attempts else None
            passed = any(a.passed for a in attempts)

            if passed:
                completed += 1

            module_items.append(
                ModuleProgressItem(
                    module_id=mod.id,
                    module_title=mod.title,
                    module_order=mod.order_index,
                    total_assessment_questions=total_q,
                    attempts_count=attempts_count,
                    last_score=last_score,
                    passed=passed,
                )
            )

        total_modules = len(modules)
        progress_pct = (
            round((completed / total_modules) * 100, 2)
            if total_modules > 0
            else 0.0
        )

        return CourseProgressSummary(
            course_id=course.id,
            course_title=course.title,
            total_modules=total_modules,
            completed_modules=completed,
            progress_percent=progress_pct,
            modules=module_items,
        )

    async def get_all_progress(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> tuple[list[CourseProgressSummary], float]:
        from app.models.course import CourseEnrollment

        enrollments_r = await db.execute(
            select(CourseEnrollment).where(
                CourseEnrollment.user_id == user_id
            )
        )
        enrollments = enrollments_r.scalars().all()

        course_summaries: list[CourseProgressSummary] = []
        total_pct = 0.0
        count = 0

        for enrollment in enrollments:
            try:
                summary = await self.get_course_progress(
                    db, user_id, enrollment.course_id
                )
                course_summaries.append(summary)
                total_pct += summary.progress_percent
                count += 1
            except ValueError:
                continue

        overall = round(total_pct / count, 2) if count > 0 else 0.0
        return course_summaries, overall


user_assessment_repository = UserAssessmentRepository()
