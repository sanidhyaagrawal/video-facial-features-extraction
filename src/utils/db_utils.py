import os
import MySQL
import json
from consts import Status, MySQLConsts, ModelConsts

class DBUtils():
    @staticmethod
    def update_status(status: str, trailId: int, userId: int, geoChatId: int) -> None:
        sql = f"""
            INSERT INTO {MySQLConsts.LOG_TABLE} (trailId, userId, geoChatId)
            VALUES ({trailId}, {userId}, {geoChatId})
            ON DUPLICATE KEY UPDATE status='{status}'
        """
        MySQL.execute_query_in_prod(sql)

    @staticmethod
    def update_trail_info(geoChatId: int, status: str, has_faces: bool, people: list, modelVersion: str = ModelConsts.MODEL_VERSION) -> None:
        has_faces = 1 if has_faces else 0
        
        sql =   f"""UPDATE {MySQLConsts.LOG_TABLE}
                    SET 
                    status='{status}',
                    modelVersion= '{modelVersion}',
                    hasFaces= {has_faces},
                    peopleCount= {len(people)},
                    peopleJson= '{json.dumps(people)}',"""
        if has_faces:
            sql +=  f"""primaryGender= {people[0]['gender']},
                        primaryAge= {people[0]['age']},
                        primaryPersonDuration= {people[0]['duration']},"""
            if people[0]['skin_tone_score'] != None:
                sql += f"""primarySkinToneScore= {people[0]['skin_tone_score']},
                           primarySkinTone= '{people[0]['skin_tone']}',"""
        # remove last comma
        sql = sql.rstrip(',') + ' WHERE geoChatId=' + str(geoChatId)
        MySQL.execute_query_in_prod(sql)

    @staticmethod
    def check_if_already_processed(geoChatId: int) -> bool:
        statuses = f"'{Status.SUCCESS}','{Status.PICKED}','{Status.FAILED}'"
        sql = f"""
            SELECT status 
            FROM {MySQLConsts.LOG_TABLE} 
            WHERE geoChatId = {geoChatId} AND status IN ({statuses})
        """
        if len(MySQL.get_prod_data(sql)) > 0:
            return True
        else:
            return False

    @staticmethod
    def get_userId(trailId: int) -> int:
        sql = f"""
            SELECT userId 
            FROM userTrails 
            WHERE trailListId = {trailId};
            """
        data = MySQL.get_prod_data(sql)
        if len(data) > 0:
            return data.iloc[0].userId
        else:
            return -1
