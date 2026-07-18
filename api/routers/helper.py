from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import pandas as pd
import logging
from typing import Optional
from api.utils import execute_query

logger = logging.getLogger(__name__)
router = APIRouter()


class CountryResponse(BaseModel):
    """Response model for a single country."""
    id: int = Field(..., description="Country ID")
    name: str = Field(..., description="Country name")
    short_name: Optional[str] = Field(None, description="Country short name")
    emoji: Optional[str] = Field(None, description="Country flag emoji")
    teams_count: int = Field(..., description="Number of teams from this country")


class CountriesListResponse(BaseModel):
    """Response model for a country list."""
    countries: list[CountryResponse] = Field(..., description="Country list")
    total_countries: int = Field(..., description="Total number of countries")


class SportResponse(BaseModel):
    """Response model for a single sport."""
    id: int = Field(..., description="Sport ID")
    name: str = Field(..., description="Sport name")
    teams_count: int = Field(..., description="Number of teams in this sport")


class SportsListResponse(BaseModel):
    """Response model for a sport list."""
    sports: list[SportResponse] = Field(..., description="Sport list")
    total_sports: int = Field(..., description="Total number of sports")


class SeasonResponse(BaseModel):
    """Response model for a single season."""
    id: int = Field(..., description="Season ID")
    years: str = Field(..., description="Season years (e.g. 2023/24)")
    matches_count: int = Field(..., description="Number of matches in the season")


class SeasonsListResponse(BaseModel):
    """Response model for a season list."""
    seasons: list[SeasonResponse] = Field(..., description="Season list")
    total_seasons: int = Field(..., description="Total number of seasons")


class SpecialRoundResponse(BaseModel):
    """Response model for a single special round."""
    id: int = Field(..., description="Special round ID")
    name: str = Field(..., description="Special round name")


class SpecialRoundsListResponse(BaseModel):
    """Response model for a special round list."""
    special_rounds: list[SpecialRoundResponse] = Field(
        ..., description="Special round list")
    total_special_rounds: int = Field(
        ..., description="Total number of special rounds")


@router.get("/helper", tags=["Helper"])
async def helper_info():
    """Return module metadata and available endpoints."""
    return {
        "module": "EkstraBet Helper API",
        "version": "1.0.0",
        "description": "Reference data endpoints for countries, sports and seasons",
        "endpoints": [
            "GET /helper/countries - Country list",
            "GET /helper/sports - Sport list",
            "GET /helper/seasons - Season list",
            "GET /helper/special-rounds - Special round list",
        ],
    }


@router.get(
    "/helper/countries",
    response_model=CountriesListResponse,
    tags=["Helper"])
async def get_countries():
    """
    Return all countries in the system.

    Helper endpoint for listing countries used to filter teams and other data.
    """
    try:
        query = """
        SELECT 
            c.ID as id,
            c.NAME as name,
            c.SHORT as short_name,
            c.EMOJI as emoji,
            COUNT(t.ID) as teams_count
        FROM countries c
        LEFT JOIN teams t ON c.ID = t.COUNTRY
        GROUP BY c.ID, c.NAME, c.SHORT, c.EMOJI
        ORDER BY c.NAME
        """
        countries_df = execute_query(query)
        countries = []
        for _, row in countries_df.iterrows():
            countries.append({
                "id": int(row['id']),
                "name": str(row['name']),
                "short_name": str(row['short_name']) if pd.notna(row['short_name']) else None,
                "emoji": str(row['emoji']) if pd.notna(row['emoji']) else None,
                "teams_count": int(row['teams_count'] or 0)
            })
        return {
            "countries": countries,
            "total_countries": len(countries)
        }
    except Exception as e:
        logger.error(f"Error in get_countries: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch country list")

@router.get("/helper/sports", response_model=SportsListResponse, tags=["Helper"])
async def get_sports():
    """
    Return all sports in the system.

    Helper endpoint for listing sports used to filter teams and other data.
    """
    try:
        query = """
        SELECT 
            s.ID as id,
            s.NAME as name,
            COUNT(t.ID) as teams_count
        FROM sports s
        LEFT JOIN teams t ON s.ID = t.SPORT_ID
        GROUP BY s.ID, s.NAME
        ORDER BY s.NAME
        """
        sports_df = execute_query(query)
        sports = []
        for _, row in sports_df.iterrows():
            sports.append({
                "id": int(row['id']),
                "name": str(row['name']),
                "teams_count": int(row['teams_count'] or 0)
            })
        return {
            "sports": sports,
            "total_sports": len(sports)
        }
    except Exception as e:
        logger.error(f"Error in get_sports: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch sport list")

@router.get("/helper/seasons", response_model=SeasonsListResponse, tags=["Helper"])
async def get_seasons():
    """
    Return all seasons in the system.

    Helper endpoint for listing seasons used to filter team stats and other data.
    """
    try:
        query = """
        SELECT 
            s.ID as id,
            s.YEARS as years,
            COUNT(m.ID) as matches_count
        FROM seasons s
        LEFT JOIN matches m ON s.ID = m.SEASON
        GROUP BY s.ID, s.YEARS
        ORDER BY s.YEARS DESC
        """
        seasons_df = execute_query(query)
        seasons = []
        for _, row in seasons_df.iterrows():
            seasons.append({
                "id": int(row['id']),
                "years": str(row['years']),
                "matches_count": int(row['matches_count'] or 0)
            })
        return {
            "seasons": seasons,
            "total_seasons": len(seasons)
        }
    except Exception as e:
        logger.error(f"Error in get_seasons: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch season list")

@router.get(
    "/helper/special-rounds",
    response_model=SpecialRoundsListResponse,
    tags=["Helper"])
async def get_special_rounds():
    """
    Return all special rounds in the system.

    Helper endpoint for listing special rounds used to filter cup matches
    and other special competitions.
    """
    try:
        query = """
        SELECT 
            ID as id,
            NAME as name
        FROM special_rounds
        ORDER BY ID
        """
        special_rounds_df = execute_query(query)
        special_rounds = []
        for _, row in special_rounds_df.iterrows():
            special_rounds.append({
                "id": int(row['id']),
                "name": str(row['name'])
            })
        return {
            "special_rounds": special_rounds,
            "total_special_rounds": len(special_rounds)
        }
    except Exception as e:
        logger.error(f"Error in get_special_rounds: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch special round list")
