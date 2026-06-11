"""Repositorio de evaluaciones de módulo."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment_option import AssessmentOption
from app.models.assessment_question import AssessmentQuestion
from app.models.module_assessment import ModuleAssessment


class ModuleAssessmentRepository:
    async def get_by_module(
        self, db: AsyncSession, module_id: int
    ) -> ModuleAssessment | None:
        r = await db.execute(
            select(ModuleAssessment)
            .where(ModuleAssessment.module_id == module_id)
            .options(
                selectinload(ModuleAssessment.questions).selectinload(
                    AssessmentQuestion.options
                )
            )
        )
        return r.scalar_one_or_none()

    async def get_by_id(self, db: AsyncSession, assessment_id: int) -> ModuleAssessment | None:
        r = await db.execute(
            select(ModuleAssessment)
            .where(ModuleAssessment.id == assessment_id)
            .options(
                selectinload(ModuleAssessment.questions).selectinload(
                    AssessmentQuestion.options
                )
            )
        )
        return r.scalar_one_or_none()

    async def create_with_questions(
        self,
        db: AsyncSession,
        *,
        module_id: int,
        passing_score: int,
        questions_data: list[dict],
    ) -> ModuleAssessment:
        assessment = ModuleAssessment(
            module_id=module_id,
            passing_score=passing_score,
        )
        db.add(assessment)
        await db.flush()
        await db.refresh(assessment)

        for qdata in questions_data:
            question = AssessmentQuestion(
                assessment_id=assessment.id,
                question_text=qdata["question_text"],
                question_type=qdata["question_type"],
                points=qdata.get("points", 1),
                order_index=qdata.get("order_index", 0),
            )
            db.add(question)
            await db.flush()
            await db.refresh(question)

            for odata in qdata["options"]:
                option = AssessmentOption(
                    question_id=question.id,
                    option_text=odata["option_text"],
                    is_correct=odata.get("is_correct", False),
                )
                db.add(option)

        await db.flush()
        return await self.get_by_id(db, assessment.id)

    async def delete(self, db: AsyncSession, assessment: ModuleAssessment) -> None:
        await db.delete(assessment)

    async def get_with_correct(
        self, db: AsyncSession, assessment_id: int
    ) -> ModuleAssessment | None:
        return await self.get_by_id(db, assessment_id)

    async def get_student_view(
        self, db: AsyncSession, assessment_id: int
    ) -> ModuleAssessment | None:
        return await self.get_by_id(db, assessment_id)


module_assessment_repository = ModuleAssessmentRepository()
