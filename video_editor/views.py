from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, LoginForm
from django.conf import settings
import boto3
import json

# Create your views here.

def index(request):
    return render(request, 'index.html')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, email=email, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})

@login_required
def dashboard(request):
    muted_video_url = None
    if request.method == 'POST' and request.FILES.get('video'):
        video_file = request.FILES['video']
        
        # Configure AWS clients with explicit region
        s3_client = boto3.client('s3',
                                 aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                 aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                                 region_name=settings.AWS_S3_REGION_NAME)
        
        lambda_client = boto3.client('lambda',
                                     aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                     aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                                     region_name=settings.AWS_S3_REGION_NAME)
        
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        s3_key = f'uploads/{request.user.id}/{video_file.name}'
        
        try:
            s3_client.upload_fileobj(video_file, bucket_name, s3_key)
            
            lambda_payload = {
                'bucket': bucket_name,
                'key': s3_key,
                'user_id': str(request.user.id)
            }
            
            response = lambda_client.invoke(
                FunctionName='ffmpeg-video-muter',
                InvocationType='RequestResponse',
                Payload=json.dumps(lambda_payload)
            )
            
            result = json.loads(response['Payload'].read())
            muted_video_url = result.get('muted_video_url')
            
        except Exception as e:
            print(f"Error: {e}")
    
    return render(request, 'dashboard.html', {'muted_video_url': muted_video_url})
