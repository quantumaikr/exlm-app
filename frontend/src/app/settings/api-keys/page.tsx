'use client';

import { useState, useEffect } from 'react';
import { Plus, Key, Copy, Trash2, AlertCircle, Check } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { format } from 'date-fns';
import ko from 'date-fns/locale/ko';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { apiKeysService } from '@/services/api-keys';

interface APIKey {
  id: string;
  name: string;
  key_prefix: string;
  description?: string;
  is_active: boolean;
  expires_at?: string;
  last_used_at?: string;
  created_at: string;
}

export default function APIKeysPage() {
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showKeyDialog, setShowKeyDialog] = useState(false);
  const [newKey, setNewKey] = useState('');
  const [copied, setCopied] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    expires_in_days: '',
  });

  const fetchApiKeys = async () => {
    try {
      setLoading(true);
      const keys = await apiKeysService.getApiKeys();
      setApiKeys(keys);
    } catch (error) {
      toast.error('API 키를 불러오는데 실패했습니다');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApiKeys();
  }, []);

  const handleCreate = async () => {
    try {
      const response = await apiKeysService.createApiKey({
        name: formData.name,
        description: formData.description || undefined,
        expires_in_days: formData.expires_in_days ? parseInt(formData.expires_in_days) : undefined,
      });
      
      setNewKey(response.full_key);
      setShowCreateDialog(false);
      setShowKeyDialog(true);
      
      // Reset form
      setFormData({
        name: '',
        description: '',
        expires_in_days: '',
      });
      
      // Refresh list
      fetchApiKeys();
      
      toast.success('API 키가 생성되었습니다');
    } catch (error) {
      toast.error('API 키 생성에 실패했습니다');
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('정말로 이 API 키를 삭제하시겠습니까?')) return;
    
    try {
      await apiKeysService.deleteApiKey(id);
      toast.success('API 키가 삭제되었습니다');
      fetchApiKeys();
    } catch (error) {
      toast.error('API 키 삭제에 실패했습니다');
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(newKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      toast.success('API 키가 복사되었습니다');
    } catch (error) {
      toast.error('복사에 실패했습니다');
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return '-';
    return format(new Date(dateString), 'PPP', { locale: ko });
  };

  const isExpired = (expiresAt?: string) => {
    if (!expiresAt) return false;
    return new Date(expiresAt) < new Date();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">API 키</h1>
          <p className="text-muted-foreground mt-2">
            API를 통해 exlm 플랫폼에 액세스하기 위한 키를 관리합니다
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="mr-2 h-4 w-4" />
          새 API 키
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>API 키 목록</CardTitle>
          <CardDescription>
            생성된 API 키는 한 번만 표시됩니다. 안전한 곳에 보관하세요.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
            </div>
          ) : apiKeys.length === 0 ? (
            <div className="text-center py-8">
              <Key className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">아직 API 키가 없습니다</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>이름</TableHead>
                  <TableHead>키 프리픽스</TableHead>
                  <TableHead>상태</TableHead>
                  <TableHead>마지막 사용</TableHead>
                  <TableHead>만료일</TableHead>
                  <TableHead>생성일</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {apiKeys.map((key) => (
                  <TableRow key={key.id}>
                    <TableCell>
                      <div>
                        <div className="font-medium">{key.name}</div>
                        {key.description && (
                          <div className="text-sm text-muted-foreground">
                            {key.description}
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <code className="text-sm">{key.key_prefix}...</code>
                    </TableCell>
                    <TableCell>
                      {key.is_active && !isExpired(key.expires_at) ? (
                        <Badge variant="success">활성</Badge>
                      ) : isExpired(key.expires_at) ? (
                        <Badge variant="destructive">만료됨</Badge>
                      ) : (
                        <Badge variant="secondary">비활성</Badge>
                      )}
                    </TableCell>
                    <TableCell>{formatDate(key.last_used_at)}</TableCell>
                    <TableCell>{formatDate(key.expires_at)}</TableCell>
                    <TableCell>{formatDate(key.created_at)}</TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDelete(key.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>새 API 키 생성</DialogTitle>
            <DialogDescription>
              API 키는 생성 후 한 번만 표시됩니다
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="name">이름 *</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="프로덕션 API 키"
              />
            </div>
            <div>
              <Label htmlFor="description">설명</Label>
              <Input
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="프로덕션 환경에서 사용"
              />
            </div>
            <div>
              <Label htmlFor="expires">만료 기간 (일)</Label>
              <Input
                id="expires"
                type="number"
                value={formData.expires_in_days}
                onChange={(e) => setFormData({ ...formData, expires_in_days: e.target.value })}
                placeholder="비워두면 만료되지 않음"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              취소
            </Button>
            <Button onClick={handleCreate} disabled={!formData.name}>
              생성
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Key Display Dialog */}
      <Dialog open={showKeyDialog} onOpenChange={setShowKeyDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>API 키가 생성되었습니다</DialogTitle>
          </DialogHeader>
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              이 API 키는 다시 표시되지 않습니다. 지금 복사하여 안전한 곳에 보관하세요.
            </AlertDescription>
          </Alert>
          <div className="space-y-4">
            <div>
              <Label>API 키</Label>
              <div className="flex items-center space-x-2 mt-1">
                <Input
                  value={newKey}
                  readOnly
                  className="font-mono text-sm"
                />
                <Button
                  size="icon"
                  variant="outline"
                  onClick={handleCopy}
                >
                  {copied ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button onClick={() => setShowKeyDialog(false)}>
              확인
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}