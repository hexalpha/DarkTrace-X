import asyncio
import httpx
from app.core.config import get_settings


async def main():
    base=get_settings().lm_studio_base_url.rstrip('/')
    async with httpx.AsyncClient(timeout=90) as client:
        models=(await client.get(base+'/models')).json().get('data',[])
        for item in models:
            model=item['id']
            if 'embed' in model.lower():
                continue
            try:
                response=await client.post(base+'/chat/completions',json={'model':model,'messages':[{'role':'user','content':'Reply with exactly: Connection verified'}],'max_tokens':64,'stream':False})
                if response.is_success:
                    choice=response.json()['choices'][0]
                    content=choice['message'].get('content')
                    print(model, 'HTTP', response.status_code, 'text characters', len(content or ''), 'finish reason', choice.get('finish_reason'),flush=True)
                    if content:
                        break
                else:
                    # Local diagnostic contains only this fixed benign prompt, no keys or tenant data.
                    error=response.json().get('error',{})
                    print(model,'HTTP',response.status_code,'detail:',str(error)[:500],flush=True)
            except Exception as exc:
                print(model, type(exc).__name__,flush=True)


if __name__=='__main__':
    asyncio.run(main())
