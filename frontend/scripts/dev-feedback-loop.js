#!/usr/bin/env node

/**
 * 개발 피드백 루프 자동화 스크립트
 * 프론트엔드 개발 중 발생하는 일반적인 오류들을 자동으로 감지하고 수정
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

class DevFeedbackLoop {
  constructor() {
    this.projectRoot = process.cwd();
    this.fixes = [];
  }

  log(message, type = 'info') {
    const colors = {
      info: '\x1b[36m',
      success: '\x1b[32m',
      warning: '\x1b[33m',
      error: '\x1b[31m',
      reset: '\x1b[0m'
    };
    
    console.log(`${colors[type]}[${type.toUpperCase()}]${colors.reset} ${message}`);
  }

  async checkAndFixTailwindCSS() {
    this.log('Checking Tailwind CSS configuration...');
    
    const tailwindConfigPath = path.join(this.projectRoot, 'tailwind.config.ts');
    const globalsCssPath = path.join(this.projectRoot, 'src/app/globals.css');
    
    // CSS 파일에서 사용되는 CSS 변수 확인
    if (fs.existsSync(globalsCssPath)) {
      const cssContent = fs.readFileSync(globalsCssPath, 'utf8');
      
      // border-border 클래스 사용 확인
      if (cssContent.includes('border-border')) {
        this.log('Found border-border usage in globals.css');
        
        // Tailwind 설정에 border 색상이 정의되어 있는지 확인
        if (fs.existsSync(tailwindConfigPath)) {
          const configContent = fs.readFileSync(tailwindConfigPath, 'utf8');
          
          if (!configContent.includes('border: "hsl(var(--border))"')) {
            this.log('Adding missing border color configuration to tailwind.config.ts', 'warning');
            
            // 자동 수정: border 색상 추가
            const updatedConfig = configContent.replace(
              /colors: {/,
              `colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",`
            );
            
            fs.writeFileSync(tailwindConfigPath, updatedConfig);
            this.fixes.push('Added missing Tailwind CSS color variables');
            this.log('Fixed Tailwind CSS configuration', 'success');
          }
        }
      }
    }
  }

  async checkAndFixMissingDependencies() {
    this.log('Checking for missing dependencies...');
    
    const packageJsonPath = path.join(this.projectRoot, 'package.json');
    if (!fs.existsSync(packageJsonPath)) {
      this.log('package.json not found', 'error');
      return;
    }
    
    const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
    const dependencies = { ...packageJson.dependencies, ...packageJson.devDependencies };
    
    // 필수 UI 라이브러리 확인
    const requiredPackages = [
      'tailwindcss-animate',
      '@radix-ui/react-slot',
      'class-variance-authority',
      'clsx',
      'tailwind-merge'
    ];
    
    const missingPackages = requiredPackages.filter(pkg => !dependencies[pkg]);
    
    if (missingPackages.length > 0) {
      this.log(`Missing packages: ${missingPackages.join(', ')}`, 'warning');
      
      try {
        this.log('Installing missing packages...', 'info');
        execSync(`npm install ${missingPackages.join(' ')}`, { stdio: 'inherit' });
        this.fixes.push(`Installed missing packages: ${missingPackages.join(', ')}`);
        this.log('Successfully installed missing packages', 'success');
      } catch (error) {
        this.log('Failed to install missing packages', 'error');
      }
    }
  }

  async checkAndFixComponentImports() {
    this.log('Checking component imports...');
    
    // src/components 디렉토리 확인
    const componentsDir = path.join(this.projectRoot, 'src/components');
    
    if (!fs.existsSync(componentsDir)) {
      this.log('Creating components directory structure...', 'info');
      
      // 기본 디렉토리 구조 생성
      const dirs = [
        'src/components/ui',
        'src/lib'
      ];
      
      dirs.forEach(dir => {
        const fullPath = path.join(this.projectRoot, dir);
        if (!fs.existsSync(fullPath)) {
          fs.mkdirSync(fullPath, { recursive: true });
        }
      });
      
      // 기본 utils 파일 생성
      const utilsPath = path.join(this.projectRoot, 'src/lib/utils.ts');
      if (!fs.existsSync(utilsPath)) {
        const utilsContent = `import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
`;
        fs.writeFileSync(utilsPath, utilsContent);
        this.fixes.push('Created lib/utils.ts');
      }
      
      this.log('Created missing directory structure', 'success');
    }
  }

  async checkAndFixESLintIssues() {
    this.log('Checking ESLint configuration...');
    
    try {
      // ESLint 실행
      const output = execSync('npx eslint src --ext .ts,.tsx --format json', { 
        encoding: 'utf8',
        stdio: 'pipe'
      });
      
      const results = JSON.parse(output);
      const errorCount = results.reduce((total, result) => total + result.errorCount, 0);
      
      if (errorCount > 0) {
        this.log(`Found ${errorCount} ESLint errors`, 'warning');
        
        try {
          execSync('npx eslint src --ext .ts,.tsx --fix', { stdio: 'inherit' });
          this.fixes.push('Fixed ESLint issues');
          this.log('Fixed ESLint issues', 'success');
        } catch (error) {
          this.log('Some ESLint issues require manual fixing', 'warning');
        }
      }
    } catch (error) {
      // ESLint가 설치되지 않았거나 설정이 없는 경우
      this.log('ESLint not configured or not installed', 'info');
    }
  }

  async checkAndFixTypeScript() {
    this.log('Checking TypeScript configuration...');
    
    try {
      const output = execSync('npx tsc --noEmit --pretty false', { 
        encoding: 'utf8',
        stdio: 'pipe'
      });
      
      this.log('TypeScript check passed', 'success');
    } catch (error) {
      this.log('TypeScript errors found', 'warning');
      console.log(error.stdout);
      
      // 일반적인 TypeScript 오류 자동 수정
      await this.fixCommonTypeScriptErrors();
    }
  }

  async fixCommonTypeScriptErrors() {
    this.log('Attempting to fix common TypeScript errors...', 'info');
    
    // 예: 누락된 타입 정의 추가
    const typesDir = path.join(this.projectRoot, 'src/types');
    if (!fs.existsSync(typesDir)) {
      fs.mkdirSync(typesDir, { recursive: true });
      
      // 기본 타입 정의 생성
      const globalTypesContent = `// Global type definitions
export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface Model {
  id: string;
  name: string;
  base_model: string;
  training_method: string;
  status: string;
}

export interface Dataset {
  id: string;
  name: string;
  size: number;
  format: string;
}
`;
      fs.writeFileSync(path.join(typesDir, 'index.ts'), globalTypesContent);
      this.fixes.push('Created basic type definitions');
    }
  }

  async generateReport() {
    this.log('\n=== 개발 피드백 루프 실행 완료 ===', 'success');
    
    if (this.fixes.length > 0) {
      this.log('적용된 수정사항:', 'info');
      this.fixes.forEach(fix => {
        this.log(`  ✓ ${fix}`, 'success');
      });
    } else {
      this.log('수정이 필요한 문제가 발견되지 않았습니다.', 'success');
    }
    
    this.log('\n다음 단계: npm run dev를 실행하여 개발 서버를 시작하세요.', 'info');
  }

  async run() {
    this.log('🔄 개발 피드백 루프 시작...', 'info');
    
    try {
      await this.checkAndFixTailwindCSS();
      await this.checkAndFixMissingDependencies();
      await this.checkAndFixComponentImports();
      await this.checkAndFixESLintIssues();
      await this.checkAndFixTypeScript();
      
      await this.generateReport();
    } catch (error) {
      this.log(`오류 발생: ${error.message}`, 'error');
      process.exit(1);
    }
  }
}

// 스크립트가 직접 실행된 경우
if (require.main === module) {
  const feedbackLoop = new DevFeedbackLoop();
  feedbackLoop.run().catch(console.error);
}

module.exports = DevFeedbackLoop;