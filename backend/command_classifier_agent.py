import os
import json
import boto3
from dotenv import load_dotenv
from datetime import datetime
import requests
import uuid

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(__file__), '../config/.env'))

class CommandClassifier:
    def __init__(self):
        
        # 設置 AWS Bedrock 客戶端
        # 使用bedrock-agent-runtime而不是bedrock來解決invoke_agent調用錯誤
        self.client = boto3.client("bedrock-agent-runtime", region_name="us-west-2")
        self.agent_id = "Q4CUJFUA8G"
        # 添加agent alias ID
        self.agent_alias_id = "YLRWOY9QOR"
        
        # 加载参考数据
        #json_path = os.path.join(os.path.dirname(__file__), '../../assets/command_type.json')
        json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'assets', 'command_type.json'))
        with open(json_path, 'r', encoding='utf-8') as f:
            self.reference_data = json.load(f)
        
        # 定义可用的函数
        self.available_functions = [{
            "function_name": "web_search",
            "description": "搜索網絡獲取實時信息",
            "parameters": [{
                "name": "query",
                "type": "string",
                "description": "搜索關鍵詞"
            }]
        }]
        
        # 為了與recorder共享數據
        self.speaker_db = None
        self.speaker_data_file = None
        
    def _send_to_agent(self, prompt):
        """發送提示詞到 Bedrock Agent 並獲取回應"""
        try:
            # 使用固定的sessionId以提高一致性
            session_id = "test-session-001"
            
            response = self.client.invoke_agent(
                agentId = self.agent_id,
                agentAliasId = self.agent_alias_id,
                inputText = prompt,
                sessionId = session_id
            )
            
            # 處理響應
            if hasattr(response, 'get') and 'completion' in response and hasattr(response['completion'], '__iter__'):
                # 處理EventStream對象
                event_stream = response['completion']
                completion_text = ""
                for event in event_stream:
                    if 'chunk' in event and 'bytes' in event['chunk']:
                        try:
                            chunk_bytes = event['chunk']['bytes']
                            chunk_text = chunk_bytes.decode('utf-8')
                            completion_text += chunk_text
                        except Exception as e:
                            pass
                return completion_text
            # else:
            #     # 嘗試其他可能的回應格式
            #     if hasattr(response, 'get'):
            #         if 'output' in response:
            #             return response['output']
            #         if 'text' in response:
            #             return response['text']
            #         if 'response' in response:
            #             return response['response']
            #         if 'message' in response:
            #             if isinstance(response['message'], dict) and 'content' in response['message']:
            #                 return response['message']['content']
            #             return response['message']
            #         if 'content' in response:
            #             return response['content']
                
            #     # 如果無法提取內容，返回默認值
            #     return "聊天"
            
        except Exception as e:
            print(f"代理調用錯誤: {str(e)}")
            return "無法獲取代理回應"
        
    def classify_command(self, text):
        """使用 Bedrock Agent 對命令進行分類"""
        # 構建提示詞，包含參考示例
        examples = "\n".join([f"- 輸入：{item['command']}  類型：{item['command_type']}" for item in self.reference_data])
        
        prompt = f"""
        根据以下示例對命令進行分類。

        示例：
        {examples}

        請對以下輸入進行分類：
        輸入："{text}"
        
        請只回復以下三種類型之一：
        - 聊天
        - 查詢
        - 行動
        
        只需回復類型，不需要其他解釋。
        """

        # 打印提示詞
        print("\n=== 提示詞內容 ===")
        print(prompt)
        print("=== 提示詞結束 ===\n")
        
        result = self._send_to_agent(prompt).strip()
        
        # 打印模型响应
        print(f"代理響應: {result}\n")
        
        # 直接根據包含的字符進行分類並返回結果
        if '查' in result or '詢' in result:
            print(f"分類結果: 查詢 (由於包含 '查' 或 '詢')")
            return '查詢'
        elif '行' in result or '動' in result:
            print(f"分類結果: 行動 (由於包含 '行' 或 '動')")
            return '行動'
        else:
            print(f"分類結果: 聊天 (預設分類)")
            return '聊天'
        
    def chat_with_gemini(self, text, speaker_id=None):
        """与 Bedrock Agent 进行聊天"""
        # 添加歷史對話上下文
        context = ""
        if speaker_id and self.speaker_db and "speakers" in self.speaker_db and speaker_id in self.speaker_db["speakers"]:
            conversations = self.speaker_db["speakers"][speaker_id].get("conversations", [])
            if conversations:
                last_conversations = conversations[-5:]  # 只取最近的5條對話
                context = "之前的對話：\n"
                for conv in last_conversations:
                    context += f"用戶: {conv.get('query', '')}\n助手: {conv.get('response', '')}\n"
        
        prompt = f"""
        你是一個友善且記憶力很好的AI助手，請用自然、友好的方式回應用戶的對話。
        請用繁體中文回覆。
        回答使用者的問題之前，如果記憶中已有相關資訊，請根據記憶直接回答。
        若記憶中找不到，才根據常識或合理推測回答。
        {context}
        
        用戶說：{text}
        """
        
        print("\n=== 聊天提示詞內容 ===")
        print(prompt)
        print("=== 提示詞結束 ===\n")
        
        result = self._send_to_agent(prompt).strip()
        
        print(f"代理回應: {result}\n")
        
        # 更新對話歷史
        if speaker_id and self.speaker_db and "speakers" in self.speaker_db and speaker_id in self.speaker_db["speakers"]:
            if "conversations" not in self.speaker_db["speakers"][speaker_id]:
                self.speaker_db["speakers"][speaker_id]["conversations"] = []
            
            self.speaker_db["speakers"][speaker_id]["conversations"].append({
                "timestamp": datetime.now().isoformat(),
                "query": text,
                "response": result
            })
            
            # 如果存在保存方法，則保存更新
            if hasattr(self, '_save_speaker_db') and callable(getattr(self, '_save_speaker_db')):
                self._save_speaker_db()
                
        return result

    def save_chat_history(self, command, response, command_type):
        """保存聊天历史到JSON文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        chat_data = {
            "timestamp": timestamp,
            "command": command,
            "response": response,
            "command_type": command_type
        }
        
        # 确保目录存在
        #save_dir = os.path.join(os.path.dirname(__file__), '../../data/chat_history')
        save_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'chat_history'))
        os.makedirs(save_dir, exist_ok=True)
        
        # 保存到JSON文件
        file_path = os.path.join(save_dir, f"chat_{timestamp}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(chat_data, f, ensure_ascii=False, indent=2)
            
        print(f"聊天記錄已保存至: {file_path}\n")

    def web_search(self, query):
        """執行網絡搜索"""
        search_api_key = os.getenv('GOOGLE_SEARCH_API_KEY')
        cx = os.getenv('GOOGLE_SEARCH_CX')
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': search_api_key,
            'cx': cx,
            'q': query
        }
        
        try:
            response = requests.get(url, params=params)
            results = response.json()
            
            if 'items' in results:
                search_results = []
                for item in results['items'][:3]:  # 只取前3個結果
                    search_results.append({
                        'title': item['title'],
                        'snippet': item['snippet'],
                        'link': item['link']
                    })
                return search_results
            return []
        except Exception as e:
            print(f"搜索出錯: {str(e)}")
            return []

    def handle_query(self, text, speaker_id=None):
        # 添加歷史對話上下文
        context = ""
        if speaker_id and self.speaker_db and "speakers" in self.speaker_db and speaker_id in self.speaker_db["speakers"]:
            conversations = self.speaker_db["speakers"][speaker_id].get("conversations", [])
            if conversations:
                last_conversations = conversations[-3:]  # 只取最近的3條對話
                context = "之前的對話：\n"
                for conv in last_conversations:
                    context += f"用戶: {conv.get('query', '')}\n助手: {conv.get('response', '')}\n"
        
        # 先判斷是否可以通過記憶回答
        memory_check_prompt = f"""
        {context}
        
        用戶提問：{text}
        
        請判斷是否可以僅憑記憶中的內容回答這個問題？
        如果可以，請直接提供完整的回答。
        如果不可以，請只回覆"需要搜索"。
        
        判斷依據：
        1. 記憶中如果有與問題直接相關的資訊，可以直接回答
        2. 如果問題是關於之前對話中已討論過的內容，可以直接回答
        3. 如果問題需要新的、未知的或最新的資訊，則需要搜索
        """
        
        print("\n=== 記憶檢查提示詞內容 ===")
        print(memory_check_prompt)
        print("=== 提示詞結束 ===\n")
        
        memory_response = self._send_to_agent(memory_check_prompt).strip()
        
        print(f"記憶檢查回應: {memory_response}\n")
        
        # 如果回應不是"需要搜索"，表示可以直接用記憶回答
        if "需要搜索" not in memory_response:
            print("使用記憶回答問題，不進行搜索")
            
            # 更新對話歷史
            if speaker_id and self.speaker_db and "speakers" in self.speaker_db and speaker_id in self.speaker_db["speakers"]:
                if "conversations" not in self.speaker_db["speakers"][speaker_id]:
                    self.speaker_db["speakers"][speaker_id]["conversations"] = []
                
                self.speaker_db["speakers"][speaker_id]["conversations"].append({
                    "timestamp": datetime.now().isoformat(),
                    "query": text,
                    "response": memory_response
                })
                
                # 如果存在保存方法，則保存更新
                if hasattr(self, '_save_speaker_db') and callable(getattr(self, '_save_speaker_db')):
                    self._save_speaker_db()
                    
            return memory_response
        
        # 如果無法從記憶中回答，則進行網絡搜索
        print("記憶中無相關資訊，進行網絡搜索...")
        lambda_client = boto3.client('lambda', region_name='us-west-2')
        resp = lambda_client.invoke(
            FunctionName='query4',
            InvocationType='RequestResponse',
            Payload=json.dumps({'query': text})
        )

        search_results = json.load(resp['Payload'])
        # 生成回应
        results_prompt = f"""
        {context}

        基於以下搜索結果，請用繁體中文總結一個完整的回答：
        回答使用者的問題之前，要結合記憶和搜索結果。

        搜索結果：
        {json.dumps(search_results, ensure_ascii=False, indent=2)}
        """
        
        final_response = self._send_to_agent(results_prompt)
        
        # 更新對話歷史
        if speaker_id and self.speaker_db and "speakers" in self.speaker_db and speaker_id in self.speaker_db["speakers"]:
            if "conversations" not in self.speaker_db["speakers"][speaker_id]:
                self.speaker_db["speakers"][speaker_id]["conversations"] = []
            
            self.speaker_db["speakers"][speaker_id]["conversations"].append({
                "timestamp": datetime.now().isoformat(),
                "query": text,
                "response": final_response
            })
            
            # 如果存在保存方法，則保存更新
            if hasattr(self, '_save_speaker_db') and callable(getattr(self, '_save_speaker_db')):
                self._save_speaker_db()
                
        return final_response.strip()

    def save_query_history(self, command, response, command_type):
        """保存查詢歷史到JSON文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        query_data = {
            "timestamp": timestamp,
            "command": command,
            "response": response,
            "command_type": command_type
        }
        
        # 确保目录存在
        save_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'query_history'))
        #save_dir = os.path.join(os.path.dirname(__file__), '../../data/query_history')
        os.makedirs(save_dir, exist_ok=True)
        
        # 保存到JSON文件
        file_path = os.path.join(save_dir, f"query_{timestamp}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(query_data, f, ensure_ascii=False, indent=2)
            
        print(f"查詢記錄已保存至: {file_path}\n")

    def handle_movement(self, text, speaker_id=None):
        """處理行動類型的命令"""
        # 加载动作部署配置
        movement_json_path = os.path.join(os.path.dirname(__file__), '../../assets/movement_deployment.json')
        with open(movement_json_path, 'r', encoding='utf-8') as f:
            movement_data = json.load(f)
            
        # 添加歷史對話上下文
        context = ""
        if speaker_id and self.speaker_db and "speakers" in self.speaker_db and speaker_id in self.speaker_db["speakers"]:
            conversations = self.speaker_db["speakers"][speaker_id].get("conversations", [])
            if conversations:
                last_conversations = conversations[-3:]  # 只取最近的3條對話
                context = "之前的對話：\n"
                for conv in last_conversations:
                    context += f"用戶: {conv.get('query', '')}\n助手: {conv.get('response', '')}\n"
                    
        prompt = f"""
        {context}
        
        你是一個專業的機器人動作規劃助手。請根據以下系統設定和用戶的任務，生成詳細的動作順序和說明。

        系統可用的動作清單：
        {json.dumps(movement_data['動作清單'], ensure_ascii=False, indent=2)}

        參考任務範例：
        {json.dumps(movement_data['任務拆解'], ensure_ascii=False, indent=2)}

        當前用戶任務：{text}

        請按照以下格式返回：
        {{
            "動作順序": ["動作代號1", "動作代號2", ...],
            "說明": [
                "詳細步驟1",
                "詳細步驟2",
                ...
            ]
        }}

        請確保：
        1. 動作順序使用動作清單中的代號
        2. 說明要詳細且符合實際執行順序
        3. 回覆必須是有效的JSON格式，並使用```json 包裹
        4. 如果用戶任務無法生成有效的動作計劃，請回覆"無法生成有效的動作計劃"
        """
        
        print("\n=== 行動規劃提示詞內容 ===")
        print(prompt)
        print("=== 提示詞結束 ===\n")
        
        result = self._send_to_agent(prompt).strip()
        
        print(f"代理回應: {result}\n")
        
        try:
            # 解析JSON回應
            # 首先檢查是否包含```json標記
            if "```json" in result:
                # 提取JSON部分
                json_str = result.split("```json")[1].split("```")[0].strip()
            else:
                json_str = result.strip()
            
            movement_plan = json.loads(json_str)
            
            # 驗證JSON格式是否正確
            if not isinstance(movement_plan, dict) or \
               '動作順序' not in movement_plan or \
               '說明' not in movement_plan or \
               not isinstance(movement_plan['動作順序'], list) or \
               not isinstance(movement_plan['說明'], list):
                raise ValueError("JSON格式不符合要求")
                
            # 更新對話歷史
            if speaker_id and self.speaker_db and "speakers" in self.speaker_db and speaker_id in self.speaker_db["speakers"]:
                if "conversations" not in self.speaker_db["speakers"][speaker_id]:
                    self.speaker_db["speakers"][speaker_id]["conversations"] = []
                
                self.speaker_db["speakers"][speaker_id]["conversations"].append({
                    "timestamp": datetime.now().isoformat(),
                    "query": text,
                    "response": json.dumps(movement_plan, ensure_ascii=False)
                })
                
                # 如果存在保存方法，則保存更新
                if hasattr(self, '_save_speaker_db') and callable(getattr(self, '_save_speaker_db')):
                    self._save_speaker_db()
                    
            return movement_plan
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"警告：無法解析回應為JSON格式 - {str(e)}")
            return {
                "動作順序": [],
                "說明": ["無法生成有效的動作計劃"]
            }

    def save_movement_history(self, command, response, command_type):
        """保存行動歷史到JSON文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        movement_data = {
            "timestamp": timestamp,
            "command": command,
            "movement_plan": response,
            "command_type": command_type
        }
        
        # 确保目录存在
        #save_dir = os.path.join(os.path.dirname(__file__), '../../data/movement_history')
        save_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'movement_history'))
        os.makedirs(save_dir, exist_ok=True)
        
        # 保存到JSON文件
        file_path = os.path.join(save_dir, f"movement_{timestamp}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(movement_data, f, ensure_ascii=False, indent=2)
            
        print(f"行動計劃已保存至: {file_path}\n")
        
    # 添加用於保存speaker_db的方法，與recorder共享
    def _save_speaker_db(self):
        """將語者資料庫儲存到磁碟"""
        if not self.speaker_db or not self.speaker_data_file:
            print("[Warning] 無法保存語者資料庫：未設置資料庫或文件路徑")
            return
            
        speakers_copy = {"speakers": {}}
        for spk_id, data in self.speaker_db["speakers"].items():
            speakers_copy["speakers"][spk_id] = {
                "created_at": data.get("created_at", datetime.now().isoformat()),
                "conversations": data.get("conversations", [])
            }
            
            if "embeddings" in data:
                embeddings_list = []
                for emb in data["embeddings"]:
                    if hasattr(emb, 'tolist'):  # 如果是numpy陣列
                        embeddings_list.append(emb.tolist())
                    else:  # 已經是列表
                        embeddings_list.append(emb)
                speakers_copy["speakers"][spk_id]["embeddings"] = embeddings_list
                
        with open(self.speaker_data_file, "w", encoding='utf-8') as f:
            json.dump(speakers_copy, f, ensure_ascii=False, indent=2)
        print(f"[Info] 語者資料庫已更新，目前共有 {len(self.speaker_db['speakers'])} 位說話者。")

if __name__ == "__main__":
    # 创建分类器实例
    classifier = CommandClassifier()
    
    # 测试用例
    test_commands = [
        "剛剛和你說話的是誰"
    ]
    
    print("開始測試命令分類：\n")
    
    # 测试每个命令
    for command in test_commands:
        print(f"測試命令: {command}")
        command_type = classifier.classify_command(command)
        print(f"分類結果: {command_type}")
        
        if command_type == '聊天':
            chat_response = classifier.chat_with_gemini(command)
            classifier.save_chat_history(command, chat_response, command_type)
        elif command_type == '查詢':
            query_response = classifier.handle_query(command)
            classifier.save_query_history(command, query_response, command_type)
            print(f"查詢結果: {query_response}")
        elif command_type == "行動":
            movement_plan = classifier.handle_movement(command)
            classifier.save_movement_history(command, movement_plan, command_type)
            print(f"行動計劃：")
            print(json.dumps(movement_plan, ensure_ascii=False, indent=2))
            
        print("-" * 50) 
        