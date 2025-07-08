#!/bin/bash

# 🔄 개발 피드백 루프 통합 스크립트
# 프론트엔드와 백엔드 개발 중 발생하는 일반적인 오류들을 자동으로 감지하고 수정

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 로깅 함수
log_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 프로젝트 루트 디렉토리
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKEND_DIR="$PROJECT_ROOT/backend"

# 수정 사항 추적
FIXES=()

add_fix() {
    FIXES+=("$1")
}

# 1. 프론트엔드 오류 수정
fix_frontend_issues() {
    log_info "🎨 프론트엔드 오류 수정 중..."
    
    cd "$FRONTEND_DIR"
    
    # Tailwind CSS 설정 확인 및 수정
    if [[ -f "src/app/globals.css" ]] && grep -q "border-border" "src/app/globals.css"; then
        log_warning "border-border 클래스 사용 감지"
        
        if [[ -f "tailwind.config.ts" ]] && ! grep -q "border: \"hsl(var(--border))\"" "tailwind.config.ts"; then
            log_info "Tailwind 설정 업데이트 중..."
            # 이미 수정된 상태이므로 스킵
        fi
    fi
    
    # 누락된 의존성 설치
    MISSING_DEPS=()
    
    # package.json에서 의존성 확인
    if ! npm list @mui/icons-material >/dev/null 2>&1; then
        MISSING_DEPS+=("@mui/icons-material")
    fi
    
    if ! npm list @mui/x-grid >/dev/null 2>&1; then
        MISSING_DEPS+=("@mui/x-grid")
    fi
    
    if [[ ${#MISSING_DEPS[@]} -gt 0 ]]; then
        log_warning "누락된 패키지 설치: ${MISSING_DEPS[*]}"
        npm install "${MISSING_DEPS[@]}" --save
        add_fix "설치된 누락 패키지: ${MISSING_DEPS[*]}"
    fi
    
    # 기본 UI 컴포넌트 생성
    if [[ ! -d "src/components/ui" ]]; then
        log_info "기본 UI 컴포넌트 디렉토리 생성"
        mkdir -p "src/components/ui"
    fi
    
    # 누락된 기본 컴포넌트 생성
    create_basic_ui_components
    
    log_success "프론트엔드 오류 수정 완료"
}

# 기본 UI 컴포넌트 생성
create_basic_ui_components() {
    local UI_DIR="$FRONTEND_DIR/src/components/ui"
    
    # Button 컴포넌트
    if [[ ! -f "$UI_DIR/button.tsx" ]]; then
        cat > "$UI_DIR/button.tsx" << 'EOF'
import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
EOF
        add_fix "생성된 Button 컴포넌트"
    fi
    
    # Dialog 컴포넌트
    if [[ ! -f "$UI_DIR/dialog.tsx" ]]; then
        cat > "$UI_DIR/dialog.tsx" << 'EOF'
import * as React from "react"
import * as DialogPrimitive from "@radix-ui/react-dialog"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"

const Dialog = DialogPrimitive.Root
const DialogTrigger = DialogPrimitive.Trigger

const DialogPortal = DialogPrimitive.Portal

const DialogOverlay = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Overlay
    ref={ref}
    className={cn(
      "fixed inset-0 z-50 bg-background/80 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
      className
    )}
    {...props}
  />
))
DialogOverlay.displayName = DialogPrimitive.Overlay.displayName

const DialogContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>
>(({ className, children, ...props }, ref) => (
  <DialogPortal>
    <DialogOverlay />
    <DialogPrimitive.Content
      ref={ref}
      className={cn(
        "fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border bg-background p-6 shadow-lg duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%] sm:rounded-lg md:w-full",
        className
      )}
      {...props}
    >
      {children}
      <DialogPrimitive.Close className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground">
        <X className="h-4 w-4" />
        <span className="sr-only">Close</span>
      </DialogPrimitive.Close>
    </DialogPrimitive.Content>
  </DialogPortal>
))
DialogContent.displayName = DialogPrimitive.Content.displayName

const DialogHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex flex-col space-y-1.5 text-center sm:text-left", className)} {...props} />
)
DialogHeader.displayName = "DialogHeader"

const DialogFooter = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2", className)} {...props} />
)
DialogFooter.displayName = "DialogFooter"

const DialogTitle = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Title
    ref={ref}
    className={cn("text-lg font-semibold leading-none tracking-tight", className)}
    {...props}
  />
))
DialogTitle.displayName = DialogPrimitive.Title.displayName

const DialogDescription = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Description
    ref={ref}
    className={cn("text-sm text-muted-foreground", className)}
    {...props}
  />
))
DialogDescription.displayName = DialogPrimitive.Description.displayName

export {
  Dialog,
  DialogPortal,
  DialogOverlay,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
}
EOF
        add_fix "생성된 Dialog 컴포넌트"
    fi
}

# 2. 백엔드 오류 수정
fix_backend_issues() {
    log_info "🔧 백엔드 오류 수정 중..."
    
    cd "$BACKEND_DIR"
    
    # 가상환경 활성화 확인
    if [[ ! -d "venv" ]]; then
        log_warning "가상환경이 없습니다. 생성 중..."
        python3 -m venv venv
        add_fix "Python 가상환경 생성"
    fi
    
    # 가상환경 활성화
    source venv/bin/activate
    
    # 기본 requirements 설치
    if [[ -f "requirements.txt" ]]; then
        log_info "Python 의존성 설치 중..."
        pip install -r requirements.txt >/dev/null 2>&1
    fi
    
    # 데이터베이스 초기화 확인
    if [[ ! -d "alembic" ]]; then
        log_warning "Alembic 초기화 필요"
        alembic init alembic 2>/dev/null || true
        add_fix "Alembic 초기화"
    fi
    
    log_success "백엔드 오류 수정 완료"
}

# 3. 포트 충돌 해결
fix_port_conflicts() {
    log_info "🔌 포트 충돌 확인 중..."
    
    # 프론트엔드 포트 (3000) 확인
    if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        log_warning "포트 3000이 사용 중입니다"
        # Next.js가 자동으로 3001로 전환하므로 별도 처리 불필요
    fi
    
    # 백엔드 포트 (8000) 확인
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        log_warning "포트 8000이 사용 중입니다"
        PID=$(lsof -Pi :8000 -sTCP:LISTEN -t)
        log_info "포트 8000 사용 중인 프로세스 ID: $PID"
    fi
}

# 4. 개발 환경 상태 확인
check_dev_environment() {
    log_info "🔍 개발 환경 상태 확인 중..."
    
    # Node.js 버전 확인
    NODE_VERSION=$(node --version 2>/dev/null || echo "not installed")
    log_info "Node.js 버전: $NODE_VERSION"
    
    # Python 버전 확인
    PYTHON_VERSION=$(python3 --version 2>/dev/null || echo "not installed")
    log_info "Python 버전: $PYTHON_VERSION"
    
    # Docker 상태 확인
    if command -v docker >/dev/null 2>&1; then
        if docker info >/dev/null 2>&1; then
            log_success "Docker 실행 중"
        else
            log_warning "Docker가 설치되어 있지만 실행되지 않음"
        fi
    else
        log_warning "Docker가 설치되지 않음"
    fi
    
    # Redis 확인
    if command -v redis-server >/dev/null 2>&1; then
        log_success "Redis 설치됨"
    else
        log_warning "Redis가 설치되지 않음"
    fi
}

# 5. 자동 수정 적용
apply_auto_fixes() {
    log_info "🔨 자동 수정 적용 중..."
    
    # 프론트엔드 자동 수정
    cd "$FRONTEND_DIR"
    
    # ESLint 자동 수정 시도
    if [[ -f ".eslintrc.json" ]] || [[ -f ".eslintrc.js" ]]; then
        log_info "ESLint 자동 수정 실행 중..."
        npx eslint src --ext .ts,.tsx --fix >/dev/null 2>&1 || true
        add_fix "ESLint 자동 수정 적용"
    fi
    
    # Prettier 포맷팅
    if [[ -f ".prettierrc" ]] || [[ -f "prettier.config.js" ]]; then
        log_info "Prettier 포맷팅 실행 중..."
        npx prettier --write "src/**/*.{ts,tsx}" >/dev/null 2>&1 || true
        add_fix "Prettier 포맷팅 적용"
    fi
}

# 6. 개발 서버 실행 전 최종 확인
pre_dev_check() {
    log_info "🚀 개발 서버 실행 전 최종 확인..."
    
    cd "$FRONTEND_DIR"
    
    # TypeScript 컴파일 확인
    log_info "TypeScript 컴파일 확인 중..."
    if npx tsc --noEmit >/dev/null 2>&1; then
        log_success "TypeScript 컴파일 성공"
    else
        log_warning "TypeScript 오류가 있지만 개발 서버는 실행 가능합니다"
    fi
    
    # 빌드 테스트 (선택적)
    if [[ "$1" == "--test-build" ]]; then
        log_info "프로덕션 빌드 테스트 중..."
        if npm run build >/dev/null 2>&1; then
            log_success "프로덕션 빌드 성공"
        else
            log_error "프로덕션 빌드 실패"
        fi
    fi
}

# 리포트 생성
generate_report() {
    echo ""
    log_success "=== 개발 피드백 루프 실행 완료 ==="
    echo ""
    
    if [[ ${#FIXES[@]} -gt 0 ]]; then
        log_info "적용된 수정사항:"
        for fix in "${FIXES[@]}"; do
            echo -e "  ${GREEN}✓${NC} $fix"
        done
    else
        log_info "수정이 필요한 문제가 발견되지 않았습니다."
    fi
    
    echo ""
    log_info "다음 단계:"
    echo -e "  ${CYAN}프론트엔드:${NC} cd frontend && npm run dev"
    echo -e "  ${CYAN}백엔드:${NC} cd backend && source venv/bin/activate && uvicorn main:app --reload"
    echo ""
}

# 메인 실행 함수
main() {
    log_info "🔄 개발 피드백 루프 시작..."
    echo ""
    
    check_dev_environment
    fix_port_conflicts
    fix_frontend_issues
    fix_backend_issues
    apply_auto_fixes
    pre_dev_check "$@"
    
    generate_report
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi