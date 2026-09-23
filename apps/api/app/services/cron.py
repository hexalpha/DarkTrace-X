"""Five-field UTC cron with bounded lists, ranges and steps."""
BOUNDS=((0,59),(0,23),(1,31),(1,12),(0,6))


def field_values(field, lower, upper):
    values=set()
    for piece in field.split(','):
        bits=piece.split('/')
        if len(bits)>2:
            raise ValueError('Invalid cron step')
        step=int(bits[1]) if len(bits)==2 else 1
        if step<1 or step>upper-lower+1:
            raise ValueError('Invalid cron step')
        interval=bits[0]
        if interval in {'*','?'}:
            first,last=lower,upper
        elif '-' in interval:
            first,last=map(int,interval.split('-'))
        else:
            first=int(interval);last=upper if len(bits)==2 else first
        if not lower<=first<=last<=upper:
            raise ValueError('Cron field outside permitted range')
        values.update(range(first,last+1,step))
    return values


def parse(expression):
    fields=expression.split()
    if len(fields)!=5:
        raise ValueError('Five cron fields required')
    return [field_values(field,*bounds) for field,bounds in zip(fields,BOUNDS)]


def due(expression, now):
    fields=expression.split(); values=parse(expression)
    day=now.day in values[2]; weekday=(now.weekday()+1)%7 in values[4]
    calendar=(day or weekday) if fields[2] not in {'*','?'} and fields[4] not in {'*','?'} else day and weekday
    return now.minute in values[0] and now.hour in values[1] and now.month in values[3] and calendar
