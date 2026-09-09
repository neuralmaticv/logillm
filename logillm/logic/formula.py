from dataclasses import dataclass


@dataclass(frozen=True)
class Var:
    name: str

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class Not:
    operand: Formula

    def __str__(self) -> str:
        return f"~{self.operand}"


@dataclass(frozen=True)
class And:
    left: Formula
    right: Formula

    def __str__(self) -> str:
        return f"({self.left} & {self.right})"


@dataclass(frozen=True)
class Or:
    left: Formula
    right: Formula

    def __str__(self) -> str:
        return f"({self.left} | {self.right})"


@dataclass(frozen=True)
class Implies:
    left: Formula
    right: Formula

    def __str__(self) -> str:
        return f"({self.left} -> {self.right})"


@dataclass(frozen=True)
class Iff:
    left: Formula
    right: Formula

    def __str__(self) -> str:
        return f"({self.left} <-> {self.right})"


Formula = Var | Not | And | Or | Implies | Iff
