import frontmatter
import tempfile
import os


_VALID_MD = """---
entity_type: project
entity_name: test_project
title: Test Project
description: Un proyecto de prueba
tags: [python, docker]
---

# Introduccion

Este es un proyecto de prueba.

## Arquitectura

La arquitectura es simple.

### Componentes

Componente A y Componente B.
"""

_NO_ENTITY_MD = """---
title: Sin Entidad
description: Un documento sin entity_name
---

# Contenido

Texto irrelevante.
"""


def test_frontmatter_parses_entity_name():
    parsed = frontmatter.loads(_VALID_MD)
    assert parsed.metadata["entity_name"] == "test_project"
    assert parsed.metadata["entity_type"] == "project"
    assert parsed.metadata["title"] == "Test Project"
    assert "python" in parsed.metadata["tags"]


def test_frontmatter_no_entity_name():
    parsed = frontmatter.loads(_NO_ENTITY_MD)
    assert "entity_name" not in parsed.metadata


def test_frontmatter_content_separated():
    parsed = frontmatter.loads(_VALID_MD)
    assert "Introduccion" in parsed.content
    assert "Arquitectura" in parsed.content
    assert parsed.metadata != {}


def test_markdown_header_splitting():
    from langchain_text_splitters import MarkdownHeaderTextSplitter

    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

    parsed = frontmatter.loads(_VALID_MD)
    splits = splitter.split_text(parsed.content)

    assert len(splits) >= 3
    headers_found = set()
    for split in splits:
        for key in ["Header 1", "Header 2", "Header 3"]:
            if key in split.metadata:
                headers_found.add(split.metadata[key])
    assert "Introduccion" in headers_found
    assert "Arquitectura" in headers_found
    assert "Componentes" in headers_found


def test_chunk_enrichment_prefix():
    from langchain_text_splitters import MarkdownHeaderTextSplitter

    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

    parsed = frontmatter.loads(_VALID_MD)
    splits = splitter.split_text(parsed.content)

    for split in splits:
        split.metadata.update(parsed.metadata)

    for split in splits:
        entidad = split.metadata.get("entity_name", "Portafolio")
        seccion = split.metadata.get("Header 3",
                    split.metadata.get("Header 2",
                        split.metadata.get("Header 1", "General")))

        enriched = f"[Entidad: {entidad} | Seccion: {seccion}]\n{split.page_content}"

        assert enriched.startswith(f"[Entidad: {entidad} | Seccion: {seccion}]")
        assert "| Seccion:" in enriched


def test_entity_name_in_metadata():
    parsed = frontmatter.loads(_VALID_MD)
    assert parsed.metadata["entity_name"] == "test_project"
    assert "." not in parsed.metadata["entity_name"]
    assert "/" not in parsed.metadata["entity_name"]
